from __future__ import annotations

from typing import Any

import torch
from loguru import logger


class ExplainableUnlearning:
    """Explainable AI for machine unlearning.

    Provides explanations for unlearning decisions by analyzing:
    - Feature importance via gradient-based attribution
    - Attention pattern changes before/after unlearning
    - Influence contributions of deleted samples
    - Reasoning traces for algorithm selection
    """

    def __init__(self) -> None:
        self._explanations: dict[int, dict] = {}

    def explain_unlearning(
        self,
        request_id: int,
        algorithm: str,
        deleted_sample_ids: list[int],
        model_before=None,
        model_after=None,
        tokenizer=None,
        sample_contents: list[str] | None = None,
    ) -> dict[str, Any]:
        logger.info(f"Generating explanation for request {request_id}")

        explanation: dict[str, Any] = {
            "request_id": request_id,
            "algorithm": algorithm,
            "num_deleted": len(deleted_sample_ids),
            "algorithm_reasoning": self._explain_algorithm_choice(algorithm, len(deleted_sample_ids)),
            "feature_importance": [],
            "attention_analysis": {},
            "weight_changes": {},
            "summary": "",
        }

        if model_before and model_after and tokenizer:
            explanation["weight_changes"] = self._compute_weight_changes(model_before, model_after)

            if sample_contents:
                explanation["feature_importance"] = self._compute_feature_importance(
                    model_before, tokenizer, sample_contents[:5]
                )

            explanation["attention_analysis"] = self._analyze_attention_changes(
                model_before, model_after, tokenizer
            )

        explanation["summary"] = self._generate_summary(explanation)
        self._explanations[request_id] = explanation
        return explanation

    def _explain_algorithm_choice(self, algorithm: str, num_deleted: int) -> str:
        reasons = {
            "sisa": f"Selected SISA (full retrain) for {num_deleted} samples. "
                    "SISA provides the strongest deletion guarantee by completely retraining "
                    "the model shard on retained data only.",
            "bad_teacher": f"Selected Bad Teacher for {num_deleted} samples. "
                          "Gradient ascent on deleted samples maximizes loss, effectively "
                          "unlearning their influence without full retraining.",
            "influence_functions": f"Selected Influence Functions for {num_deleted} samples. "
                                  "Computes the influence of each training sample and applies "
                                  "inverse Hessian-weighted corrections.",
            "certified_removal": f"Selected Certified Removal for {num_deleted} samples. "
                                "Provides formal differential privacy guarantees with "
                                "quantifiable removal bounds.",
            "catastrophic_forgetting": f"Selected Catastrophic Forgetting for {num_deleted} samples. "
                                      "Perturbs model weights to break associations with "
                                      "deleted data patterns.",
            "relu_erasure": f"Selected ReLU Erasure for {num_deleted} samples. "
                           "Scales LoRA weights to erase representational capacity "
                           "for deleted patterns.",
        }
        return reasons.get(algorithm, f"Algorithm {algorithm} selected for {num_deleted} samples.")

    def _compute_feature_importance(
        self, model, tokenizer, texts: list[str]
    ) -> list[dict[str, Any]]:
        importance_scores = []
        model.eval()
        for text in texts:
            if not text:
                continue
            try:
                inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
                inputs = {k: v.to(model.device) for k, v in inputs.items()}

                embeddings = inputs["input_ids"].float().requires_grad_(True)
                outputs = model(inputs_embeds=model.get_input_embeddings()(embeddings.long()))
                loss = outputs.logits.sum()
                loss.backward()

                if embeddings.grad is not None:
                    token_importance = embeddings.grad.abs().mean(dim=-1).squeeze()
                    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
                    top_k = min(5, len(tokens))
                    top_indices = token_importance.topk(top_k).indices.tolist()

                    importance_scores.append({
                        "text_preview": text[:100],
                        "top_tokens": [
                            {"token": tokens[i], "score": round(token_importance[i].item(), 4)}
                            for i in top_indices
                            if i < len(tokens)
                        ],
                    })
            except Exception:
                continue
        return importance_scores

    def _analyze_attention_changes(
        self, model_before, model_after, tokenizer
    ) -> dict[str, Any]:
        try:
            test_text = "This is a test sentence for attention analysis."
            inputs = tokenizer(test_text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model_before.device) for k, v in inputs.items()}

            model_before.eval()
            with torch.no_grad():
                out_before = model_before(**inputs, output_attentions=True)

            model_after.eval()
            with torch.no_grad():
                out_after = model_after(**inputs, output_attentions=True)

            if out_before.attentions and out_after.attentions:
                attn_before = out_before.attentions[-1].mean(dim=1).squeeze()
                attn_after = out_after.attentions[-1].mean(dim=1).squeeze()
                diff = (attn_before - attn_after).abs().mean().item()
                return {
                    "attention_shift": round(diff, 4),
                    "num_layers": len(out_before.attentions),
                    "interpretation": (
                        "Minimal attention change" if diff < 0.01
                        else "Moderate attention redistribution" if diff < 0.05
                        else "Significant attention pattern changes"
                    ),
                }
        except Exception:
            pass
        return {"attention_shift": 0.0, "interpretation": "Unable to analyze"}

    def _compute_weight_changes(self, model_before, model_after) -> dict[str, Any]:
        changes = {}
        total_change = 0.0
        count = 0

        before_dict = {n: p.data for n, p in model_before.named_parameters() if "lora" in n}
        after_dict = {n: p.data for n, p in model_after.named_parameters() if "lora" in n}

        for name in before_dict:
            if name in after_dict:
                diff = (before_dict[name] - after_dict[name]).abs()
                mean_change = diff.mean().item()
                max_change = diff.max().item()
                changes[name] = {
                    "mean_change": round(mean_change, 6),
                    "max_change": round(max_change, 6),
                }
                total_change += mean_change
                count += 1

        return {
            "parameters_changed": count,
            "total_mean_change": round(total_change / max(count, 1), 6),
            "details": changes,
        }

    def _generate_summary(self, explanation: dict) -> str:
        algo = explanation["algorithm"]
        num = explanation["num_deleted"]
        weight_changes = explanation.get("weight_changes", {})
        params_changed = weight_changes.get("parameters_changed", 0)
        total_change = weight_changes.get("total_mean_change", 0)

        summary = f"Unlearning operation used {algo} to remove {num} samples. "
        if params_changed > 0:
            summary += f"Modified {params_changed} LoRA parameters with average change of {total_change:.6f}. "
        summary += explanation.get("algorithm_reasoning", "")
        return summary

    def get_explanation(self, request_id: int) -> dict[str, Any] | None:
        return self._explanations.get(request_id)

    def get_feature_attribution(
        self, model, tokenizer, text: str, target_token_idx: int = -1
    ) -> dict[str, Any]:
        try:
            model.eval()
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            input_ids = inputs["input_ids"].clone().requires_grad_(True)
            outputs = model(inputs_embeds=model.get_input_embeddings()(input_ids))

            logits = outputs.logits
            if target_token_idx == -1:
                target_token_idx = logits.shape[1] - 1

            target_logit = logits[0, target_token_idx, :].max()
            target_logit.backward()

            if input_ids.grad is not None:
                attributions = input_ids.grad.abs().squeeze().tolist()
                if isinstance(attributions, float):
                    attributions = [attributions]

                tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
                return {
                    "text": text,
                    "tokens": tokens,
                    "attributions": [
                        {"token": t, "attribution": round(a, 4)}
                        for t, a in zip(tokens, attributions)
                    ],
                }
        except Exception as e:
            logger.warning(f"Feature attribution failed: {e}")
        return {"text": text, "tokens": [], "attributions": []}
