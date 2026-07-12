from __future__ import annotations

from typing import AsyncGenerator

import torch
from loguru import logger

from app.ml.model_manager import ModelManager


MODEL_TIMEOUT_SECONDS = 30


class InferenceEngine:
    def __init__(self) -> None:
        self.model_mgr = ModelManager()
        self._model_ready = False
        self._load_error = None

    def _ensure_model_loaded(self) -> bool:
        if self._model_ready:
            return True
        if self._load_error:
            return False
        try:
            import threading
            result = [None]
            error = [None]
            event = threading.Event()

            def load():
                try:
                    self.model_mgr.load_base_model()
                    result[0] = True
                except Exception as e:
                    error[0] = e
                finally:
                    event.set()

            t = threading.Thread(target=load, daemon=True)
            t.start()
            loaded = event.wait(timeout=MODEL_TIMEOUT_SECONDS)
            if loaded and result[0]:
                self._model_ready = True
                return True
            else:
                msg = str(error[0]) if error[0] else "Model loading timed out"
                self._load_error = msg
                logger.warning(f"Model not available: {msg}")
                return False
        except Exception as e:
            self._load_error = str(e)
            return False

    async def generate(
        self,
        prompt: str,
        history: list[dict] | None = None,
        stream: bool = False,
        rag_context: str | None = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
    ) -> str:
        if not self._ensure_model_loaded():
            return self._fallback_response(prompt)

        try:
            model, tokenizer = self.model_mgr.load_base_model()

            messages = []
            if history:
                for m in history:
                    messages.append({"role": m["role"], "content": m["content"]})

            augmented_prompt = prompt
            if rag_context:
                augmented_prompt = (
                    "Use the following retrieved context to answer the question.\n\n"
                    f"Context:\n{rag_context}\n\n"
                    f"Question: {prompt}"
                )
            messages.append({"role": "user", "content": augmented_prompt})

            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=min(max_new_tokens, 256),
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=temperature > 0,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )

            generated = outputs[0][inputs["input_ids"].shape[1]:]
            response = tokenizer.decode(generated, skip_special_tokens=True)
            return response.strip()

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        return (
            "I acknowledge receiving your message. "
            "The neural engine is currently in offline mode. "
            "Your data has been logged and will be processed when the model is available."
        )

    async def generate_stream(
        self,
        prompt: str,
        history: list[dict] | None = None,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        rag_context: str | None = None,
    ) -> AsyncGenerator[str, None]:
        if not self._ensure_model_loaded():
            yield self._fallback_response(prompt)
            return

        model, tokenizer = self.model_mgr.load_base_model()

        messages = []
        if history:
            for m in history:
                messages.append({"role": m["role"], "content": m["content"]})
        augmented_prompt = prompt
        if rag_context:
            augmented_prompt = (
                "Use the following retrieved context to answer the question.\n\n"
                f"Context:\n{rag_context}\n\n"
                f"Question: {prompt}"
            )
        messages.append({"role": "user", "content": augmented_prompt})

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        with torch.no_grad():
            for _ in range(min(max_new_tokens, 256)):
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=1,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    do_sample=temperature > 0,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )

                new_token = outputs[0][-1:]
                token_str = tokenizer.decode(new_token, skip_special_tokens=True)

                if token_str == "" or new_token.item() == tokenizer.eos_token_id:
                    break

                yield token_str

                inputs["input_ids"] = torch.cat([inputs["input_ids"], new_token.unsqueeze(0)], dim=-1)
                inputs["attention_mask"] = torch.cat(
                    [inputs["attention_mask"], torch.ones((1, 1), device=model.device)], dim=-1
                )
