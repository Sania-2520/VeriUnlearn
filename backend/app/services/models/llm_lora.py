"""LLM + LoRA adapter backend (research contribution #1).

This is the *production path* for LLM unlearning: each user/data-slice owns an
independent LoRA adapter; unlearning a user means removing their adapter and,
optionally, patching the base model with a negative-gradient step. The class
only activates when ``transformers`` + ``peft`` are installed (optional
dependencies — see ``requirements-optional.txt``) and a device is available.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("veriunlearn.lora")

try:  # optional heavy deps — imported lazily on first use
    import torch  # type: ignore[import-not-found]
    from peft import LoraConfig, get_peft_model  # type: ignore[import-not-found]
    from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore[import-not-found]

    _LORA_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without optional deps
    torch = None  # type: ignore[assignment]
    _LORA_AVAILABLE = False


class LoRAUnlearnableModel:
    """PEFT LoRA adapter that can be added / removed independently.

    ``adapter`` names map 1:1 to user identities. ``unlearn_adapter`` removes
    the adapter from the model and records the removal so the audit trail can
    prove the adapter no longer exists.
    """

    model_type = "llm_lora"

    def __init__(self, base_model_name: str, adapter_name: str | None = None, device: str = "auto") -> None:
        if not _LORA_AVAILABLE:
            raise RuntimeError(
                "LoRA backend requires optional deps: pip install -r backend/requirements-optional.txt"
            )
        self.base_model_name = base_model_name
        self.device = device if device != "auto" else ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(base_model_name)
        if adapter_name:
            self.model = get_peft_model(
                self.model,
                LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, task_type="SEQ_CLS"),
                adapter_name=adapter_name,
            )
        self.active_adapter = adapter_name

    # --- UnlearnableModel protocol -------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        raise NotImplementedError("Use train_from_texts() with raw text for LLM backends")

    def train_from_texts(self, texts: list[str], labels: list[int], *, epochs: int = 1) -> dict[str, Any]:
        import torch as _torch

        self.model.train()
        optimizer = _torch.optim.AdamW(self.model.parameters(), lr=2e-4)
        encodings = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
        y = _torch.tensor(labels).to(self.device)
        loss = None
        for _ in range(epochs):
            out = self.model(**encodings, labels=y)
            loss = out.loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        return {"loss": float(loss.detach().cpu()) if loss is not None else 0.0}

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Use predict_texts() with raw text for LLM backends")

    def predict_texts(self, texts: list[str]) -> np.ndarray:
        import torch as _torch

        self.model.eval()
        encodings = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
        with _torch.no_grad():
            logits = self.model(**encodings).logits
        return _torch.softmax(logits, dim=-1).cpu().numpy()

    def weights(self) -> np.ndarray:
        raise NotImplementedError("LoRA adapters store weights in PEFT state dicts")

    def set_weights(self, weights: np.ndarray) -> None:
        raise NotImplementedError("LoRA adapters store weights in PEFT state dicts")

    def embed(self, X: np.ndarray) -> np.ndarray:
        raise NotImplementedError("Use embed_texts() for LLM backends")

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        import torch as _torch

        self.model.eval()
        encodings = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
        with _torch.no_grad():
            return self.model.base_model(**encodings).last_hidden_state.mean(dim=1).cpu().numpy()

    # --- Unlearning ----------------------------------------------------------------

    def unlearn_adapter(self, adapter_name: str) -> dict[str, Any]:
        """Independently remove an adapter; other adapters are untouched."""
        if self.active_adapter == adapter_name:
            self.model = self.model.unload()
            self.active_adapter = None
            return {"adapter": adapter_name, "removed": True, "residual_adapters": []}
        # Multiple adapters: delete just this one from the PEFT model.
        self.model.delete_adapter(adapter_name)
        remaining = [a for a in self.model.peft_config if a != adapter_name]
        return {"adapter": adapter_name, "removed": True, "residual_adapters": remaining}

    def apply_negative_gradient(self, texts: list[str], labels: list[int], *, lr: float = 1e-3) -> dict[str, Any]:
        """Gradient-ascent step to scrub influence of ``texts`` (approximate unlearning)."""
        import torch as _torch

        self.model.train()
        optimizer = _torch.optim.SGD(self.model.parameters(), lr=lr)
        encodings = self.tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(self.device)
        y = _torch.tensor(labels).to(self.device)
        out = self.model(**encodings, labels=y)
        # Maximise loss -> minimise influence of the forgotten data.
        (-out.loss).backward()
        optimizer.step()
        return {"negative_gradient": True, "loss_before_scrub": float(out.loss.detach().cpu())}
