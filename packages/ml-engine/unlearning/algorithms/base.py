from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UnlearningContext:
    target_data_ids: list[str]
    model_type: str = "transformer"
    model_name: str = ""
    data_size: int = 0
    latency_ms: int = 500
    accuracy_target: float = 0.95
    regulatory: str = "gdpr"
    config: dict = field(default_factory=dict)


@dataclass
class UnlearningResult:
    success: bool = False
    algorithm: str = ""
    processing_time_ms: int = 0
    utility_retained: float = 0.0
    error_message: Optional[str] = None
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class UnlearningAlgorithm(ABC):
    @abstractmethod
    async def unlearn(
        self, context: UnlearningContext
    ) -> UnlearningResult:
        ...

    @abstractmethod
    async def verify(
        self, context: UnlearningContext
    ) -> bool:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def theoretical_guarantee(self) -> str:
        ...
