import hashlib
import json
import logging
import math
import os
import random
import shutil
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.data import Dataset as TorchDataset

try:
    from peft import LoraConfig, PeftModel, TaskType, get_peft_model
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False

from training.data import Dataset as VDataset
from training.data import accuracy_score

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

SEEDS = ("random", "numpy", "torch", "cuda")


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _save_rng_state() -> dict[str, Any]:
    state: dict[str, Any] = {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch_cpu": torch.random.get_rng_state(),
    }
    if torch.cuda.is_available():
        state["torch_cuda"] = torch.cuda.get_rng_state_all()
    return state


def _load_rng_state(state: dict[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available() and "torch_cuda" in state:
        torch.cuda.set_rng_state_all(state["torch_cuda"])


@dataclass
class TrainingConfig:
    base_model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    # SECURITY: remote code execution from Hugging Face Hub is disabled by
    # default. Only enable ``trust_remote_code`` for vetted model repositories.
    # Pin ``hub_revision`` to an immutable commit SHA for reproducible,
    # tamper-resistant model downloads in production.
    trust_remote_code: bool = False
    hub_revision: str = ""
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: list[str] = field(
        default_factory=lambda: [
            "q_proj", "v_proj", "k_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ]
    )
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-4
    warmup_steps: int = 100
    max_seq_length: int = 512
    gradient_accumulation_steps: int = 4
    fp16: bool = True
    bf16: bool = False
    output_dir: str = "./checkpoints"
    save_steps: int = 500
    eval_steps: int = 100
    logging_steps: int = 10
    resume_from_checkpoint: Optional[str] = None
    remove_data_ids: list[str] = field(default_factory=list)
    seed: int = 42

    def config_hash(self) -> str:
        raw = json.dumps(self.__dict__, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class TrainingMetrics:
    epoch: float
    step: int
    train_loss: float
    eval_loss: Optional[float]
    learning_rate: float
    grad_norm: float
    train_samples_per_second: float
    global_step: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class CheckpointInfo:
    checkpoint_id: str
    adapter_path: str
    epoch: int
    step: int
    metrics: dict
    config_hash: str
    created_at: str
    parent_checkpoint_id: Optional[str]
    is_best: bool
    file_size_bytes: int
    sha256: str


class ConversationDataset(TorchDataset):
    def __init__(
        self,
        conversations: list[dict],
        tokenizer: Any,
        max_length: int = 512,
    ):
        self.conversations = conversations
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.conversations)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        conv = self.conversations[idx]
        instruction = conv.get("instruction", "")
        input_text = conv.get("input", "")
        output_text = conv.get("output", "")

        if input_text:
            user_content = f"{instruction}\n{input_text}"
        else:
            user_content = instruction

        messages = [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": output_text},
        ]

        has_chat_template = hasattr(self.tokenizer, "apply_chat_template") and getattr(
            self.tokenizer, "chat_template", None
        ) is not None

        if has_chat_template:
            full_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            user_only_messages = [{"role": "user", "content": user_content}]
            prompt_text = self.tokenizer.apply_chat_template(
                user_only_messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt_text = f"### Instruction:\n{user_content}\n\n### Response:\n"
            full_text = f"{prompt_text}{output_text}"

        full_encoded = self.tokenizer(
            full_text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors=None,
        )
        prompt_encoded = self.tokenizer(
            prompt_text,
            truncation=True,
            max_length=self.max_length,
            padding=False,
            return_tensors=None,
        )

        input_ids = full_encoded["input_ids"]
        attention_mask = full_encoded["attention_mask"]

        prompt_len = len(prompt_encoded["input_ids"])
        labels = [-100] * prompt_len + input_ids[prompt_len:]

        pad_len = self.max_length - len(input_ids)
        if pad_len > 0:
            pad_token_id = self.tokenizer.pad_token_id
            if pad_token_id is None:
                pad_token_id = self.tokenizer.eos_token_id if self.tokenizer.eos_token_id is not None else 0
            input_ids = input_ids + [pad_token_id] * pad_len
            attention_mask = attention_mask + [0] * pad_len
            labels = labels + [-100] * pad_len

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


class LoRATrainer:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model: Optional[nn.Module] = None
        self.tokenizer: Optional[Any] = None
        self.peft_model: Optional[Any] = None
        self.training_history: list[TrainingMetrics] = []
        self.checkpoints: list[CheckpointInfo] = []
        self._current_run_id: str = str(uuid.uuid4())
        self._peft_mode: bool = PEFT_AVAILABLE
        self._device: torch.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self._best_eval_loss: float = float("inf")
        self._parent_checkpoint_id: Optional[str] = None
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    def setup_model(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        logger.info("Loading base model: %s", self.config.base_model_name)

        tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model_name,
            trust_remote_code=self.config.trust_remote_code,
            revision=self.config.hub_revision or None,
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token_id = tokenizer.eos_token_id

        quantization_config = None
        if self.config.fp16 and self._device.type == "cuda":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

        model_kwargs: dict[str, Any] = {
            "torch_dtype": torch.float16 if self.config.fp16 else torch.float32,
        }
        if quantization_config is not None:
            model_kwargs["quantization_config"] = quantization_config
            model_kwargs["device_map"] = "auto"
        else:
            model_kwargs["device_map"] = None

        # SECURITY (B615): revision/trust_remote_code are passed as explicit
        # keywords so the supply-chain posture is auditable: remote code is
        # disabled by default and the revision (when set) pins an immutable
        # commit SHA.
        model = AutoModelForCausalLM.from_pretrained(
            self.config.base_model_name,
            trust_remote_code=self.config.trust_remote_code,
            revision=self.config.hub_revision or None,
            **model_kwargs,
        )

        if quantization_config is None:
            model = model.to(self._device)

        self.tokenizer = tokenizer

        if self._peft_mode:
            lora_config = LoraConfig(
                r=self.config.lora_r,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=self.config.lora_target_modules,
                bias="none",
                task_type=TaskType.CAUSAL_LM,
            )
            self.model = model
            self.peft_model = get_peft_model(model, lora_config)
            self.peft_model.print_trainable_parameters()
        else:
            logger.warning(
                "PEFT not available — falling back to full fine-tuning mode"
            )
            self.model = model
            self.peft_model = model

        trainable = sum(
            p.numel() for p in self.peft_model.parameters() if p.requires_grad
        )
        total = sum(p.numel() for p in self.peft_model.parameters())
        logger.info(
            "Model ready — trainable: %d / total: %.2fM (%.2f%%)",
            trainable,
            total / 1e6,
            100.0 * trainable / total if total > 0 else 0,
        )

    def prepare_dataset(
        self, conversations: list[dict]
    ) -> tuple[ConversationDataset, ConversationDataset]:
        if self.tokenizer is None:
            raise RuntimeError("Call setup_model() before prepare_dataset()")

        filtered = conversations
        if self.config.remove_data_ids:
            remove_set = set(self.config.remove_data_ids)
            filtered = [
                c for c in conversations
                if c.get("data_id") not in remove_set
            ]
            logger.info(
                "Removed %d conversations via remove_data_ids",
                len(conversations) - len(filtered),
            )

        split_idx = max(1, int(len(filtered) * 0.9))
        rng = random.Random(self.config.seed)  # nosec B311 - deterministic seeded data split
        shuffled = filtered[:]
        rng.shuffle(shuffled)  # nosec B311 - deterministic seeded data split
        train_convs = shuffled[:split_idx]
        eval_convs = shuffled[split_idx:]

        train_dataset = ConversationDataset(
            train_convs, self.tokenizer, self.config.max_seq_length
        )
        eval_dataset = ConversationDataset(
            eval_convs, self.tokenizer, self.config.max_seq_length
        )
        logger.info(
            "Dataset prepared — train: %d, eval: %d", len(train_dataset), len(eval_dataset)
        )
        return train_dataset, eval_dataset

    def train(self, conversations: list[dict]) -> list[TrainingMetrics]:
        if self.peft_model is None:
            raise RuntimeError("Call setup_model() before train()")

        _set_seed(self.config.seed)
        train_dataset, eval_dataset = self.prepare_dataset(conversations)

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            drop_last=True,
        )

        effective_batch = self.config.batch_size * self.config.gradient_accumulation_steps
        num_update_steps = (
            len(train_loader) * self.config.num_epochs
            // self.config.gradient_accumulation_steps
        )

        no_decay = ["bias", "LayerNorm.weight", "layer_norm.weight"]
        optimizer_grouped = [
            {
                "params": [
                    p
                    for n, p in self.peft_model.named_parameters()
                    if p.requires_grad and not any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.01,
            },
            {
                "params": [
                    p
                    for n, p in self.peft_model.named_parameters()
                    if p.requires_grad and any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.0,
            },
        ]
        optimizer = torch.optim.AdamW(
            optimizer_grouped, lr=self.config.learning_rate, eps=1e-8
        )

        def lr_lambda(current_step: int) -> float:
            if current_step < self.config.warmup_steps:
                return float(current_step) / float(max(1, self.config.warmup_steps))
            progress = float(current_step - self.config.warmup_steps) / float(
                max(1, num_update_steps - self.config.warmup_steps)
            )
            return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

        scaler: Optional[torch.amp.GradScaler] = None
        use_amp = self.config.fp16 and self._device.type == "cuda"
        if use_amp:
            scaler = torch.amp.GradScaler("cuda")

        global_step = 0
        epoch_offset = 0
        step_offset = 0

        if self.config.resume_from_checkpoint:
            resume_state = self.load_checkpoint(self.config.resume_from_checkpoint)
            if resume_state.get("optimizer_state_dict"):
                optimizer.load_state_dict(resume_state["optimizer_state_dict"])
            if resume_state.get("scheduler_state_dict"):
                scheduler.load_state_dict(resume_state["scheduler_state_dict"])
            if scaler is not None and resume_state.get("scaler_state_dict"):
                scaler.load_state_dict(resume_state["scaler_state_dict"])
            if resume_state.get("rng_state"):
                _load_rng_state(resume_state["rng_state"])
            global_step = resume_state.get("global_step", 0)
            epoch_offset = resume_state.get("epoch", 0)
            step_offset = resume_state.get("step", 0)
            self._parent_checkpoint_id = resume_state.get("checkpoint_id")
            logger.info(
                "Resumed from checkpoint %s at global_step=%d",
                self.config.resume_from_checkpoint,
                global_step,
            )

        run_name = f"lora_{self.config.base_model_name.split('/')[-1]}_{self._current_run_id[:8]}"

        mlflow_run = None
        if MLFLOW_AVAILABLE:
            try:
                mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "mlruns"))
                mlflow_run = mlflow.start_run(run_name=run_name)
                mlflow.log_params(self.config.__dict__)
                mlflow.log_param("peft_mode", self._peft_mode)
                mlflow.log_param("device", str(self._device))
                mlflow.log_param("trainable_params", self._get_trainable_count())
            except Exception as exc:
                logger.warning("MLflow init failed, continuing without tracking: %s", exc)
                mlflow_run = None

        try:
            for epoch in range(epoch_offset, self.config.num_epochs):
                self.peft_model.train()
                epoch_loss = 0.0
                epoch_tokens = 0
                step_in_epoch = 0
                t_epoch_start = time.monotonic()
                optimizer.zero_grad()

                for batch_idx, batch in enumerate(train_loader):
                    if epoch == epoch_offset and batch_idx < step_offset and global_step > 0:
                        continue

                    input_ids = batch["input_ids"].to(self._device)
                    attention_mask = batch["attention_mask"].to(self._device)
                    labels = batch["labels"].to(self._device)

                    if use_amp:
                        with torch.amp.autocast("cuda", dtype=torch.float16):
                            outputs = self.peft_model(
                                input_ids=input_ids,
                                attention_mask=attention_mask,
                                labels=labels,
                            )
                            loss = outputs.loss / self.config.gradient_accumulation_steps
                        scaler.scale(loss).backward()
                    else:
                        outputs = self.peft_model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                            labels=labels,
                        )
                        loss = outputs.loss / self.config.gradient_accumulation_steps
                        loss.backward()

                    real_loss = loss.item() * self.config.gradient_accumulation_steps
                    epoch_loss += real_loss
                    step_in_epoch += 1

                    tokens_in_batch = attention_mask.sum().item()
                    epoch_tokens += int(tokens_in_batch)

                    if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                        if scaler is not None:
                            scaler.unscale_(optimizer)
                            grad_norm = torch.nn.utils.clip_grad_norm_(
                                self.peft_model.parameters(), max_norm=1.0
                            )
                            scaler.step(optimizer)
                            scaler.update()
                        else:
                            grad_norm = torch.nn.utils.clip_grad_norm_(
                                self.peft_model.parameters(), max_norm=1.0
                            )
                            optimizer.step()

                        scheduler.step()
                        optimizer.zero_grad()
                        global_step += 1

                        elapsed = time.monotonic() - t_epoch_start
                        samples_per_sec = (
                            (step_in_epoch * self.config.batch_size) / elapsed
                            if elapsed > 0
                            else 0.0
                        )

                        avg_loss = epoch_loss / step_in_epoch
                        current_lr = scheduler.get_last_lr()[0]
                        grad_norm_val = (
                            grad_norm.item() if isinstance(grad_norm, torch.Tensor) else grad_norm
                        )

                        metrics = TrainingMetrics(
                            epoch=epoch + (batch_idx + 1) / len(train_loader),
                            step=global_step,
                            train_loss=avg_loss,
                            eval_loss=None,
                            learning_rate=current_lr,
                            grad_norm=grad_norm_val,
                            train_samples_per_second=samples_per_sec,
                            global_step=global_step,
                        )
                        self.training_history.append(metrics)

                        if global_step % self.config.logging_steps == 0:
                            logger.info(
                                "epoch=%.2f step=%d loss=%.4f lr=%.2e grad_norm=%.2f samples/s=%.1f",
                                metrics.epoch,
                                global_step,
                                avg_loss,
                                current_lr,
                                grad_norm_val,
                                samples_per_sec,
                            )
                            if mlflow_run is not None:
                                try:
                                    mlflow.log_metrics(
                                        {
                                            "train_loss": avg_loss,
                                            "learning_rate": current_lr,
                                            "grad_norm": grad_norm_val,
                                            "samples_per_second": samples_per_sec,
                                        },
                                        step=global_step,
                                    )
                                except Exception:
                                    logger.warning("Failed to log training metrics to MLflow", exc_info=True)

                        if (
                            self.config.eval_steps > 0
                            and global_step % self.config.eval_steps == 0
                        ):
                            eval_result = self.evaluate(eval_dataset)
                            metrics.eval_loss = eval_result["eval_loss"]

                            if mlflow_run is not None:
                                try:
                                    mlflow.log_metrics(
                                        {
                                            "eval_loss": eval_result["eval_loss"],
                                            "eval_perplexity": eval_result["eval_perplexity"],
                                        },
                                        step=global_step,
                                    )
                                except Exception:
                                    logger.warning("Failed to log eval metrics to MLflow", exc_info=True)

                            is_best = eval_result["eval_loss"] < self._best_eval_loss
                            if is_best:
                                self._best_eval_loss = eval_result["eval_loss"]
                            ckpt = self.save_checkpoint(
                                epoch, global_step, eval_result, is_best=is_best
                            )
                            self._parent_checkpoint_id = ckpt.checkpoint_id
                            logger.info(
                                "Eval at step %d — loss=%.4f, ppl=%.4f, best=%s",
                                global_step,
                                eval_result["eval_loss"],
                                eval_result["eval_perplexity"],
                                is_best,
                            )
                            self.peft_model.train()

                        if (
                            self.config.save_steps > 0
                            and global_step % self.config.save_steps == 0
                        ):
                            ckpt = self.save_checkpoint(
                                epoch, global_step, {"train_loss": avg_loss}
                            )
                            self._parent_checkpoint_id = ckpt.checkpoint_id

                epoch_elapsed = time.monotonic() - t_epoch_start
                logger.info(
                    "Epoch %d completed in %.1fs — avg_loss=%.4f",
                    epoch,
                    epoch_elapsed,
                    epoch_loss / max(1, step_in_epoch),
                )

            final_eval = self.evaluate(eval_dataset)
            final_ckpt = self.save_checkpoint(
                self.config.num_epochs - 1,
                global_step,
                final_eval,
                is_best=final_eval["eval_loss"] < self._best_eval_loss,
            )
            if final_eval["eval_loss"] < self._best_eval_loss:
                self._best_eval_loss = final_eval["eval_loss"]

            if mlflow_run is not None:
                try:
                    mlflow.log_metrics(
                        {
                            "final_eval_loss": final_eval["eval_loss"],
                            "final_eval_perplexity": final_eval["eval_perplexity"],
                        },
                        step=global_step,
                    )
                    mlflow.log_artifact(final_ckpt.adapter_path)
                except Exception:
                    logger.warning("Failed to log final metrics/artifact to MLflow", exc_info=True)

            logger.info(
                "Training complete — %d steps, final eval_loss=%.4f, perplexity=%.4f",
                global_step,
                final_eval["eval_loss"],
                final_eval["eval_perplexity"],
            )

        finally:
            if mlflow_run is not None:
                try:
                    mlflow.end_run()
                except Exception:
                    logger.warning("Failed to end MLflow run", exc_info=True)

        return self.training_history

    def save_checkpoint(
        self,
        epoch: int,
        step: int,
        metrics: dict,
        is_best: bool = False,
    ) -> CheckpointInfo:
        if self.peft_model is None:
            raise RuntimeError("No model to checkpoint")

        ckpt_id = f"ckpt_{uuid.uuid4().hex[:12]}"
        adapter_dir = os.path.join(self.config.output_dir, ckpt_id, "adapter")
        state_dir = os.path.join(self.config.output_dir, ckpt_id, "state")
        os.makedirs(adapter_dir, exist_ok=True)
        os.makedirs(state_dir, exist_ok=True)

        if self._peft_mode and hasattr(self.peft_model, "save_pretrained"):
            self.peft_model.save_pretrained(adapter_dir)
        else:
            torch.save(self.peft_model.state_dict(), os.path.join(adapter_dir, "model.pt"))

        optimizer_state_dict = None
        scheduler_state_dict = None
        rng_state = _save_rng_state()

        ckpt_info = CheckpointInfo(
            checkpoint_id=ckpt_id,
            adapter_path=adapter_dir,
            epoch=epoch,
            step=step,
            metrics=metrics,
            config_hash=self.config.config_hash(),
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_checkpoint_id=self._parent_checkpoint_id,
            is_best=is_best,
            file_size_bytes=0,
            sha256="",
        )

        state_path = os.path.join(state_dir, "training_state.json")
        serializable_info = {
            "checkpoint_id": ckpt_info.checkpoint_id,
            "epoch": ckpt_info.epoch,
            "step": ckpt_info.step,
            "metrics": ckpt_info.metrics,
            "config_hash": ckpt_info.config_hash,
            "created_at": ckpt_info.created_at,
            "parent_checkpoint_id": ckpt_info.parent_checkpoint_id,
            "is_best": ckpt_info.is_best,
            "global_step": step,
        }
        with open(state_path, "w") as f:
            json.dump(serializable_info, f, indent=2, default=str)

        ckpt_info.file_size_bytes = self._dir_size(adapter_dir)
        ckpt_info.sha256 = self._compute_sha256(adapter_dir)
        self.checkpoints.append(ckpt_info)

        logger.info(
            "Checkpoint saved: %s (step=%d, size=%d bytes, sha256=%s)",
            ckpt_id,
            step,
            ckpt_info.file_size_bytes,
            ckpt_info.sha256[:12],
        )
        return ckpt_info

    def load_checkpoint(self, checkpoint_path: str) -> dict:
        adapter_dir = checkpoint_path
        state_path = os.path.join(checkpoint_path, "..", "state", "training_state.json")
        if os.path.exists(os.path.join(checkpoint_path, "adapter")):
            adapter_dir = os.path.join(checkpoint_path, "adapter")
            state_path = os.path.join(checkpoint_path, "state", "training_state.json")

        if self._peft_mode and PEFT_AVAILABLE and self.model is not None:
            # adapter_dir is a local checkpoint directory (never a Hub repo), so
            # no remote download/revision concerns apply.
            self.peft_model = PeftModel.from_pretrained(
                self.model, adapter_dir, is_trainable=True
            )
            logger.info("LoRA adapter loaded from %s", adapter_dir)
        else:
            model_path = os.path.join(adapter_dir, "model.pt")
            if os.path.exists(model_path) and self.peft_model is not None:
                # weights_only=True blocks pickle-based RCE from tampered
                # checkpoint files (B614). State dicts are plain tensors, so
                # this is fully compatible with checkpoints this code saves.
                self.peft_model.load_state_dict(
                    torch.load(
                        model_path,
                        map_location=self._device,
                        weights_only=True,
                    )
                )
                logger.info("Full model state loaded from %s", model_path)

        state: dict[str, Any] = {}
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                state = json.load(f)

        return state

    @torch.no_grad()
    def evaluate(self, dataset: ConversationDataset) -> dict:
        if self.peft_model is None:
            raise RuntimeError("Call setup_model() before evaluate()")

        self.peft_model.eval()
        eval_loader = DataLoader(
            dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            drop_last=False,
        )

        total_loss = 0.0
        total_tokens = 0
        num_batches = 0

        for batch in eval_loader:
            input_ids = batch["input_ids"].to(self._device)
            attention_mask = batch["attention_mask"].to(self._device)
            labels = batch["labels"].to(self._device)

            use_amp = self.config.fp16 and self._device.type == "cuda"
            if use_amp:
                with torch.amp.autocast("cuda", dtype=torch.float16):
                    outputs = self.peft_model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
            else:
                outputs = self.peft_model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )

            batch_loss = outputs.loss.item()
            batch_tokens = int(attention_mask.sum().item())
            total_loss += batch_loss * batch_tokens
            total_tokens += batch_tokens
            num_batches += 1

        avg_loss = total_loss / max(1, total_tokens)
        perplexity = float(np.exp(min(avg_loss, 20.0)))

        logger.info(
            "Evaluation — loss=%.4f, perplexity=%.4f, batches=%d",
            avg_loss,
            perplexity,
            num_batches,
        )
        return {
            "eval_loss": avg_loss,
            "eval_perplexity": perplexity,
            "eval_tokens": total_tokens,
            "eval_batches": num_batches,
        }

    @torch.no_grad()
    def predict(
        self,
        instruction: str,
        input_text: str = "",
        max_new_tokens: int = 256,
    ) -> str:
        if self.peft_model is None or self.tokenizer is None:
            raise RuntimeError("Call setup_model() before predict()")

        self.peft_model.eval()

        if input_text:
            user_content = f"{instruction}\n{input_text}"
        else:
            user_content = instruction

        has_chat_template = hasattr(self.tokenizer, "apply_chat_template") and getattr(
            self.tokenizer, "chat_template", None
        ) is not None

        if has_chat_template:
            messages = [{"role": "user", "content": user_content}]
            prompt_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt_text = f"### Instruction:\n{user_content}\n\n### Response:\n"

        inputs = self.tokenizer(
            prompt_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_seq_length - max_new_tokens,
        ).to(self._device)

        use_amp = self.config.fp16 and self._device.type == "cuda"
        if use_amp:
            with torch.amp.autocast("cuda", dtype=torch.float16):
                output_ids = self.peft_model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.pad_token_id
                    or self.tokenizer.eos_token_id,
                )
        else:
            output_ids = self.peft_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.pad_token_id
                or self.tokenizer.eos_token_id,
            )

        prompt_len = inputs["input_ids"].shape[1]
        generated_ids = output_ids[0][prompt_len:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return response.strip()

    def get_adapter_info(self) -> dict:
        if self.peft_model is None:
            return {"mode": "no_model", "peft_available": PEFT_AVAILABLE}

        total_params = sum(p.numel() for p in self.peft_model.parameters())
        trainable_params = sum(
            p.numel() for p in self.peft_model.parameters() if p.requires_grad
        )

        info: dict[str, Any] = {
            "mode": "lora" if self._peft_mode else "full_finetune",
            "peft_available": PEFT_AVAILABLE,
            "total_params": total_params,
            "trainable_params": trainable_params,
            "trainable_pct": (
                100.0 * trainable_params / total_params if total_params > 0 else 0.0
            ),
            "base_model": self.config.base_model_name,
            "device": str(self._device),
            "config": {
                "lora_r": self.config.lora_r,
                "lora_alpha": self.config.lora_alpha,
                "lora_dropout": self.config.lora_dropout,
                "lora_target_modules": self.config.lora_target_modules,
            },
            "checkpoints_saved": len(self.checkpoints),
            "training_steps": len(self.training_history),
        }

        if self._peft_mode and hasattr(self.peft_model, "peft_config"):
            try:
                for task_name, task_config in self.peft_model.peft_config.items():
                    info["peft_task"] = task_name
                    info["peft_config"] = {
                        "r": task_config.r,
                        "lora_alpha": task_config.lora_alpha,
                        "lora_dropout": task_config.lora_dropout,
                        "target_modules": list(task_config.target_modules)
                        if task_config.target_modules
                        else [],
                        "bias": task_config.bias,
                    }
            except Exception:
                logger.debug("Failed to read peft_config from model", exc_info=True)

        return info

    def cleanup_old_checkpoints(self, keep_last_n: int = 5) -> list[str]:
        if len(self.checkpoints) <= keep_last_n:
            return []

        sorted_ckpts = sorted(
            self.checkpoints,
            key=lambda c: c.step,
            reverse=True,
        )

        best_ids = {c.checkpoint_id for c in self.checkpoints if c.is_best}
        keep_ids: set[str] = set()
        for ckpt in sorted_ckpts[:keep_last_n]:
            keep_ids.add(ckpt.checkpoint_id)
        keep_ids.update(best_ids)

        removed: list[str] = []
        for ckpt in sorted_ckpts:
            if ckpt.checkpoint_id not in keep_ids:
                ckpt_dir = os.path.join(self.config.output_dir, ckpt.checkpoint_id)
                if os.path.exists(ckpt_dir):
                    shutil.rmtree(ckpt_dir)
                    removed.append(ckpt.checkpoint_id)
                    logger.info("Removed old checkpoint: %s", ckpt.checkpoint_id)

        self.checkpoints = [c for c in self.checkpoints if c.checkpoint_id in keep_ids or os.path.exists(os.path.join(self.config.output_dir, c.checkpoint_id))]
        return removed

    def export_adapter(self, checkpoint_id: str, export_path: str) -> str:
        source = None
        for ckpt in self.checkpoints:
            if ckpt.checkpoint_id == checkpoint_id:
                source = ckpt.adapter_path
                break

        if source is None:
            fallback = os.path.join(self.config.output_dir, checkpoint_id, "adapter")
            if os.path.exists(fallback):
                source = fallback

        if source is None or not os.path.exists(source):
            raise FileNotFoundError(
                f"Checkpoint {checkpoint_id} not found in {self.config.output_dir}"
            )

        os.makedirs(export_path, exist_ok=True)
        dest = os.path.join(export_path, checkpoint_id)
        shutil.copytree(source, dest, dirs_exist_ok=True)
        logger.info("Exported adapter %s → %s", checkpoint_id, dest)
        return dest

    @staticmethod
    def _compute_sha256(path: str) -> str:
        h = hashlib.sha256()
        if os.path.isfile(path):
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        elif os.path.isdir(path):
            for root, _dirs, files in sorted(os.walk(path)):
                for fname in sorted(files):
                    fpath = os.path.join(root, fname)
                    h.update(os.path.relpath(fpath, path).encode())
                    with open(fpath, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _dir_size(path: str) -> int:
        total = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total

    def _get_trainable_count(self) -> int:
        if self.peft_model is None:
            return 0
        return sum(p.numel() for p in self.peft_model.parameters() if p.requires_grad)
