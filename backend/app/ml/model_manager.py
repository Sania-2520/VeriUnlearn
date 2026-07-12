from __future__ import annotations

import hashlib
from pathlib import Path

import torch
from loguru import logger
from peft import LoraConfig, PeftModel, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedModel,
    PreTrainedTokenizer,
)

from app.core.config import settings


class ModelManager:
    _instance: ModelManager | None = None
    _model: PreTrainedModel | None = None
    _tokenizer: PreTrainedTokenizer | None = None
    _adapter_loaded: str | None = None

    def __new__(cls) -> ModelManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.device = torch.device(settings.device if torch.cuda.is_available() else "cpu")
        self.model_name = settings.base_model_name
        self.cache_dir = Path(settings.model_cache_dir)
        self.adapter_dir = Path(settings.adapter_storage_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.adapter_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ModelManager initialized (device={self.device}, model={self.model_name})")

    def is_model_cached(self) -> bool:
        model_slug = self.model_name.replace("/", "--")
        snapshot_dir = self.cache_dir / f"models--{model_slug}"
        return snapshot_dir.exists() and any(snapshot_dir.iterdir())

    def load_base_model(self) -> tuple[PreTrainedModel, PreTrainedTokenizer]:
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer

        logger.info(f"Loading base model: {self.model_name}")

        quantization_config = None
        if self.device.type == "cuda" and settings.quantization_bits == 4:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        elif self.device.type == "cuda" and settings.quantization_bits == 8:
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            cache_dir=str(self.cache_dir),
            trust_remote_code=True,
            padding_side="right",
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quantization_config,
            device_map="auto" if self.device.type == "cuda" else None,
            torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
            cache_dir=str(self.cache_dir),
            trust_remote_code=True,
        )

        if settings.use_gradient_checkpointing:
            self._model.gradient_checkpointing_enable()

        logger.info(f"Base model loaded: {self.model_name}")
        return self._model, self._tokenizer

    def create_lora_adapter(self, model: PreTrainedModel) -> PeftModel:
        lora_config = LoraConfig(
            r=settings.lora_r,
            lora_alpha=settings.lora_alpha,
            lora_dropout=settings.lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        peft_model = get_peft_model(model, lora_config)
        peft_model.print_trainable_parameters()
        return peft_model

    def load_adapter(self, adapter_path: str) -> PeftModel:
        model, tokenizer = self.load_base_model()
        if self._adapter_loaded == adapter_path:
            return model

        peft_model = PeftModel.from_pretrained(model, adapter_path)
        self._adapter_loaded = adapter_path
        logger.info(f"Adapter loaded from {adapter_path}")
        return peft_model

    def save_adapter(self, model: PeftModel, name: str) -> str:
        save_path = str(self.adapter_dir / name)
        model.save_pretrained(save_path)
        self._tokenizer.save_pretrained(save_path)
        logger.info(f"Adapter saved to {save_path}")
        return save_path

    def compute_model_hash(self, adapter_path: str) -> str:
        hasher = hashlib.sha256()
        adapter_dir = Path(adapter_path)
        if adapter_dir.exists():
            for fpath in sorted(adapter_dir.rglob("*.safetensors")) or sorted(adapter_dir.rglob("*.bin")):
                with open(fpath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hasher.update(chunk)
            for fpath in sorted(adapter_dir.rglob("*.json")):
                with open(fpath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hasher.update(chunk)
        return hasher.hexdigest()

    def unload_model(self) -> None:
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        self._adapter_loaded = None
        torch.cuda.empty_cache()
        logger.info("Model unloaded from memory")

    def free_memory(self) -> None:
        torch.cuda.empty_cache()
        import gc
        gc.collect()
