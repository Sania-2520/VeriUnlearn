import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Prompt-injection heuristics
# ---------------------------------------------------------------------------
# Each entry is ``(category, regex)`` targeting the well-known injection
# vectors: instruction overrides, role/authority switches, system-prompt
# exfiltration, delimiter smuggling, verbatim-output demands and indirect
# (context-injected) instruction following. Patterns are deliberately
# conservative to keep false positives on benign prompts low; the detector is
# a defence-in-depth heuristic, not a guarantee against a determined attacker.
PROMPT_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "ignore_instructions",
        r"(?i)\bignore\s+(all\s+)?(previous|prior|the\s+above|earlier)\s+(instructions|rules|prompts?)\b",
    ),
    (
        "ignore_instructions",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|prompts?)\b",
    ),
    (
        "ignore_instructions",
        r"(?i)\bdo\s+not\s+(follow|obey)\s+(the\s+)?(above|previous|prior)\s+(instructions|rules|prompts?)\b",
    ),
    (
        "ignore_instructions",
        r"(?i)\b(forget|override|ignore)\s+(everything|all|any)\s+(above|previous|prior)\b",
    ),
    (
        "role_switch",
        r"(?i)\byou\s+are\s+now\s+(in\s+)?(developer\s+)?(mode|dan|unrestricted|unfiltered|jailbroken)\b",
    ),
    (
        "role_switch",
        r"(?i)\b(pretend|act)\s+as\s+(if\s+you\s+are\s+)?(an?\s+)?(unrestricted|unfiltered|no[-\s]rules|jailbreak)\s+(ai|assistant|model)\b",
    ),
    (
        "role_switch",
        r"(?i)\b(developer\s+mode|do\s+anything\s+now|dan\s+mode|jailbreak(\s+mode)?)\b",
    ),
    (
        "system_prompt_extraction",
        r"(?i)\b(show|reveal|print|display|output|leak|expose|paste)\s+(me\s+)?(your\s+)?(system\s+|initial\s+|hidden\s+|full\s+)?prompt\b",
    ),
    # For the ``instructions`` noun, require ``your`` or a system/initial/
    # hidden/full prefix so benign asks like "output instructions for this
    # API" are not rejected.
    (
        "system_prompt_extraction",
        r"(?i)\b(show|reveal|print|display|output|leak|expose|paste)\s+(me\s+)?(your\s+|(system|initial|hidden|full)\s+)\s*instructions\b",
    ),
    (
        "delimiter_smuggling",
        r"(?i)(<\|im_start\|>\s*system|<\|sys\|>|<\|system\|>|\[/?INST\]|<s>\[INST\])",
    ),
    # The weaker ``following`` variant requires the trailing modifier so benign
    # asks like "Output the following text in Spanish" (translation/formatting
    # tasks) are not rejected; ``above``/``entire``/``whole`` are strong signals
    # on their own.
    (
        "verbatim_output",
        r"(?i)\b(repeat|print|output)\s+(the\s+)?(above|entire|whole)\s+(text|prompt|instructions)\b",
    ),
    (
        "verbatim_output",
        r"(?i)\b(repeat|print|output)\s+(the\s+)?following\s+(text|prompt|instructions)\s+(back|verbatim|exactly)\b",
    ),
    (
        "verbatim_output",
        r"(?i)\bwrite\s+(the\s+)?(above|entire|whole|following)\s+(text|prompt|instructions)\s+(back|verbatim|exactly)\b",
    ),
    (
        "indirect_injection",
        r"(?i)\bignore\s+(the\s+)?(instructions|prompt|text|context)\s+(contained\s+in|from\s+the|in\s+the)\s+(the\s+)?(document|file|context|url|website)\b",
    ),
)


@dataclass
class PromptInjectionResult:
    """Outcome of a prompt-injection scan.

    ``detected`` is True when at least one known injection pattern matched;
    ``score`` is a 0..1 severity estimate (count of distinct categories);
    ``categories`` and ``matches`` name the signals for observability.
    """

    detected: bool = False
    score: float = 0.0
    categories: list[str] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "score": round(self.score, 3),
            "categories": self.categories,
            "matches": self.matches,
        }


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

    # ------------------------------------------------------------------
    # Prompt injection detection
    # ------------------------------------------------------------------

    def detect_prompt_injection(self, prompt: str) -> PromptInjectionResult:
        """Scan a prompt for known prompt-injection patterns.

        Returns a :class:`PromptInjectionResult` describing what was found.
        This is a heuristic (defence-in-depth) check; it does not raise.
        """
        if not isinstance(prompt, str):
            raise ValidationError("prompt must be a string")

        categories: list[str] = []
        matches: list[str] = []
        seen: set[str] = set()
        for category, pattern in PROMPT_INJECTION_PATTERNS:
            m = re.search(pattern, prompt)
            if m:
                matches.append(m.group(0)[:200])
                if category not in seen:
                    seen.add(category)
                    categories.append(category)

        detected = len(categories) > 0
        # Severity grows with the number of distinct signal categories.
        score = min(1.0, 0.35 * len(categories)) if detected else 0.0
        return PromptInjectionResult(
            detected=detected,
            score=score,
            categories=categories,
            matches=matches,
        )

    def validate_prompt_safety(
        self,
        prompt: str,
        strict: Optional[bool] = None,
    ) -> PromptInjectionResult:
        """Run :meth:`detect_prompt_injection` and enforce the policy.

        In strict mode (the default for this validator) a detected injection
        raises :class:`ValidationError` — adversarial prompts fail closed.
        In non-strict mode the signal is logged and returned for the caller
        to decide.
        """
        result = self.detect_prompt_injection(prompt)
        if result.detected:
            strict_mode = self._strict if strict is None else strict
            msg = (
                f"Prompt rejected: potential prompt injection detected "
                f"({', '.join(result.categories)})"
            )
            if strict_mode:
                raise ValidationError(msg)
            logger.warning("Prompt injection indicators detected: %s", result.categories)
        return result

    # ------------------------------------------------------------------
    # Output sanitization
    # ------------------------------------------------------------------

    def sanitize_text_output(self, text: Any, max_length: int = 32000) -> str:
        """Sanitize model output before it leaves the engine.

        Strips C0 control characters (except the tab/newline/CR trio) that
        could corrupt logs or downstream parsers, coerces non-string values,
        and caps the length to bound response size.
        """
        if not isinstance(text, str):
            text = str(text)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        return cleaned[:max_length]

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
