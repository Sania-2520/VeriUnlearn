from __future__ import annotations

from typing import Any

import torch
from datasets import Dataset
from loguru import logger
from peft import PeftModel
from torch.utils.data import DataLoader
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    get_scheduler,
)
from tqdm import tqdm

from app.core.config import settings
from app.ml.model_manager import ModelManager


class Trainer:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()
        self.device = self.model_mgr.device

    def prepare_dataset(
        self, samples: list[dict], tokenizer: AutoTokenizer
    ) -> Dataset:
        formatted = []
        for s in samples:
            if s.get("role") == "assistant":
                text = f"<|assistant|>\n{s['content']}<|end|>"
            else:
                text = f"<|user|>\n{s['content']}<|end|>"
            formatted.append({"text": text})

        dataset = Dataset.from_list(formatted)

        def tokenize_fn(examples):
            result = tokenizer(
                examples["text"],
                truncation=True,
                max_length=settings.max_seq_length,
                padding="max_length",
            )
            result["labels"] = result["input_ids"].copy()
            return result

        tokenized = dataset.map(
            tokenize_fn,
            batched=True,
            remove_columns=["text"],
        )
        return tokenized

    def train(
        self,
        dataset: Dataset,
        model: PeftModel,
        tokenizer: AutoTokenizer,
        callbacks: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        model.train()

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )

        train_dataloader = DataLoader(
            dataset,
            batch_size=settings.batch_size,
            shuffle=True,
            collate_fn=data_collator,
        )

        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=settings.learning_rate,
            weight_decay=0.01,
        )

        num_training_steps = len(train_dataloader) * settings.num_epochs
        num_warmup_steps = int(num_training_steps * settings.warmup_ratio)

        scheduler = get_scheduler(
            "cosine",
            optimizer=optimizer,
            num_warmup_steps=num_warmup_steps,
            num_training_steps=num_training_steps,
        )

        total_loss = 0.0
        metrics = {
            "train_loss": [],
            "epoch_loss": [],
            "learning_rates": [],
        }

        progress_bar = tqdm(total=num_training_steps, desc="Training")

        for epoch in range(settings.num_epochs):
            epoch_loss = 0.0
            for batch in train_dataloader:
                batch = {k: v.to(self.device) for k, v in batch.items()}

                outputs = model(**batch)
                loss = outputs.loss

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                total_loss += loss.item()
                epoch_loss += loss.item()
                progress_bar.update(1)
                progress_bar.set_postfix({"loss": f"{loss.item():.4f}", "epoch": epoch + 1})

                if callbacks and "on_step" in callbacks:
                    callbacks["on_step"]({
                        "loss": loss.item(),
                        "epoch": epoch + 1,
                        "step": progress_bar.n,
                        "lr": scheduler.get_last_lr()[0],
                    })

            avg_epoch_loss = epoch_loss / len(train_dataloader)
            metrics["epoch_loss"].append(avg_epoch_loss)
            metrics["learning_rates"].append(scheduler.get_last_lr()[0])
            logger.info(f"Epoch {epoch + 1}/{settings.num_epochs} - Loss: {avg_epoch_loss:.4f}")

        progress_bar.close()

        avg_loss = total_loss / num_training_steps
        metrics["train_loss"] = avg_loss

        logger.info(f"Training completed. Avg loss: {avg_loss:.4f}")
        return metrics

    def evaluate(
        self,
        dataset: Dataset,
        model: PeftModel,
        tokenizer: AutoTokenizer,
    ) -> dict[str, float]:
        model.eval()

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )

        eval_dataloader = DataLoader(
            dataset,
            batch_size=settings.batch_size,
            shuffle=False,
            collate_fn=data_collator,
        )

        total_loss = 0.0
        with torch.no_grad():
            for batch in tqdm(eval_dataloader, desc="Evaluating"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = model(**batch)
                total_loss += outputs.loss.item()

        avg_loss = total_loss / len(eval_dataloader)
        logger.info(f"Evaluation completed. Loss: {avg_loss:.4f}")
        return {"eval_loss": avg_loss}
