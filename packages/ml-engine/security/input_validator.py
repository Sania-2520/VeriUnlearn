import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


class InputValidator:
    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 100000
    MAX_DICT_DEPTH = 10
    MAX_FLOAT_VALUE = 1e9
    ALLOWED_MODEL_TYPES = {"transformer", "classifier", "regressor", "llm", "default"}
    ALLOWED_ALGORITHMS = {"sisa", "influence", "certified_removal", "hybrid", "ed25519", "groth16"}
    ALLOWED_REGULATORY = {"gdpr", "ccpa", "lgpd", "pdpa", "hipaa", "benchmark"}
    ALLOWED_METHODS = {"shap", "lime", "integrated_gradients", "gradient", "occlusion", "perturbation"}

    def __init__(self, strict: bool = True) -> None:
        self._strict = strict

    def validate_unlearning_request(self, data: dict) -> dict:
        errors = []
        target_ids = data.get("target_data_ids", [])
        if not isinstance(target_ids, list):
            errors.append("target_data_ids must be a list")
        elif len(target_ids) == 0:
            errors.append("target_data_ids must not be empty")
        elif len(target_ids) > self.MAX_ARRAY_LENGTH:
            errors.append(f"target_data_ids exceeds max length ({self.MAX_ARRAY_LENGTH})")

        model_type = data.get("model_type", "")
        if model_type and model_type not in self.ALLOWED_MODEL_TYPES:
            errors.append(f"model_type must be one of {self.ALLOWED_MODEL_TYPES}")

        regulatory = data.get("regulatory", "")
        if regulatory and regulatory not in self.ALLOWED_REGULATORY:
            errors.append(f"regulatory must be one of {self.ALLOWED_REGULATORY}")

        data_size = data.get("data_size", 0)
        if not isinstance(data_size, (int, float)) or data_size < 0 or data_size > 1e9:
            errors.append("data_size must be a non-negative integer <= 1e9")

        if errors:
            msg = "; ".join(errors)
            if self._strict:
                raise ValidationError(msg)
            logger.warning("Validation warnings: %s", msg)
        return data

    def validate_explain_request(self, data: dict) -> dict:
        errors = []
        method = data.get("method", "")
        if method and method.lower() not in self.ALLOWED_METHODS:
            errors.append(f"method must be one of {self.ALLOWED_METHODS}")

        samples = data.get("samples", data.get("dataset", []))
        if isinstance(samples, list) and len(samples) > self.MAX_ARRAY_LENGTH:
            errors.append(f"samples exceeds max length ({self.MAX_ARRAY_LENGTH})")

        for sample in samples if isinstance(samples, list) else []:
            if isinstance(sample, list):
                for val in sample:
                    if isinstance(val, (int, float)) and abs(val) > self.MAX_FLOAT_VALUE:
                        errors.append(f"sample value {val} exceeds max absolute value {self.MAX_FLOAT_VALUE}")
                        break

        if errors:
            msg = "; ".join(errors)
            if self._strict:
                raise ValidationError(msg)
            logger.warning("Validation warnings: %s", msg)
        return data

    def validate_prompt(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")
        if len(prompt) > self.MAX_STRING_LENGTH:
            raise ValidationError(f"prompt exceeds max length ({self.MAX_STRING_LENGTH})")
        if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', prompt):
            raise ValidationError("prompt contains control characters")
        return prompt.strip()

    def validate_adapter_name(self, name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("adapter_name must be a non-empty string")
        if len(name) > 255:
            raise ValidationError("adapter_name too long (max 255)")
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', name):
            raise ValidationError("adapter_name contains invalid characters")
        return name.strip()

    def sanitize_metadata(self, metadata: dict, max_depth: int = 5) -> dict:
        def _sanitize(obj: Any, depth: int = 0) -> Any:
            if depth > max_depth:
                return str(obj)[:100]
            if isinstance(obj, dict):
                return {str(k)[:100]: _sanitize(v, depth + 1) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v, depth + 1) for v in obj[:100]]
            if isinstance(obj, (str, int, float, bool)):
                return obj
            return str(obj)[:100]
        return _sanitize(metadata)
