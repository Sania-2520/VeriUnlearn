import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


@dataclass
class DistillationConfig:
    teacher_model_name: str = ""
    student_model_name: str = ""
    temperature: float = 4.0
    alpha: float = 0.5
    soft_target_weight: float = 0.7
    hard_target_weight: float = 0.3
    num_epochs: int = 5
    batch_size: int = 32
    learning_rate: float = 1e-4
    max_seq_length: int = 512
    output_dir: str = "./distillation_checkpoints"
    seed: int = 42


@dataclass
class DistillationMetrics:
    epoch: int
    step: int
    distillation_loss: float
    student_loss: float
    kl_divergence: float
    teacher_accuracy: float
    student_accuracy: float
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat())


@dataclass
class DistillationResult:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: dict = field(default_factory=dict)
    metrics: list[dict] = field(default_factory=list)
    final_student_accuracy: float = 0.0
    final_teacher_accuracy: float = 0.0
    compression_ratio: float = 1.0
    status: str = "completed"
    error: Optional[str] = None
    student_checkpoint_path: Optional[str] = None


class SimpleMLP(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: list[int], num_classes: int):
        super().__init__()
        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.1))
            prev = h
        layers.append(nn.Linear(prev, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class KnowledgeDistiller:
    def __init__(self, config: Optional[DistillationConfig] = None):
        self.config = config or DistillationConfig()
        self.teacher: Optional[nn.Module] = None
        self.student: Optional[nn.Module] = None
        self.history: list[DistillationMetrics] = []

    def setup_models(
        self,
        input_dim: int,
        num_classes: int,
        teacher_hidden: Optional[list[int]] = None,
        student_hidden: Optional[list[int]] = None,
    ) -> None:
        teacher_dims = teacher_hidden or [512, 256, 128]
        student_dims = student_hidden or [128, 64, 32]
        self.teacher = SimpleMLP(input_dim, teacher_dims, num_classes)
        self.student = SimpleMLP(input_dim, student_dims, num_classes)

        teacher_params = sum(p.numel() for p in self.teacher.parameters())
        student_params = sum(p.numel() for p in self.student.parameters())
        self.compression_ratio = teacher_params / max(student_params, 1)
        logger.info(
            "Models initialized — teacher: %d params, student: %d params, ratio: %.2fx",
            teacher_params, student_params, self.compression_ratio,
        )

    def set_teacher(self, teacher: nn.Module) -> None:
        self.teacher = teacher
        self.teacher.eval()

    def set_student(self, student: nn.Module) -> None:
        self.student = student

    def distill(
        self,
        train_loader: torch.utils.data.DataLoader,
        val_loader: Optional[torch.utils.data.DataLoader] = None,
    ) -> DistillationResult:
        if self.teacher is None or self.student is None:
            raise RuntimeError("Call setup_models() or set_teacher()/set_student() first")

        self.teacher.eval()
        self.student.train()

        optimizer = torch.optim.AdamW(
            self.student.parameters(),
            lr=self.config.learning_rate,
            weight_decay=1e-5,
        )

        result = DistillationResult(
            config={
                "temperature": self.config.temperature,
                "alpha": self.config.alpha,
                "soft_target_weight": self.config.soft_target_weight,
                "hard_target_weight": self.config.hard_target_weight,
                "num_epochs": self.config.num_epochs,
                "learning_rate": self.config.learning_rate,
            }
        )

        device = next(self.teacher.parameters()).device
        global_step = 0

        try:
            for epoch in range(self.config.num_epochs):
                epoch_loss = 0.0
                epoch_kl = 0.0
                epoch_student_loss = 0.0
                num_batches = 0

                for batch_idx, (inputs, targets) in enumerate(train_loader):
                    inputs = inputs.to(device)
                    targets = targets.to(device)

                    with torch.no_grad():
                        teacher_logits = self.teacher(inputs)

                    student_logits = self.student(inputs)

                    soft_teacher = F.softmax(teacher_logits / self.config.temperature, dim=-1)
                    soft_student = F.log_softmax(student_logits / self.config.temperature, dim=-1)
                    kl_loss = F.kl_div(soft_student, soft_teacher, reduction="batchmean") * (
                        self.config.temperature ** 2
                    )

                    ce_loss = F.cross_entropy(student_logits, targets)

                    loss = (
                        self.config.soft_target_weight * kl_loss
                        + self.config.hard_target_weight * ce_loss
                    )

                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.student.parameters(), max_norm=1.0)
                    optimizer.step()

                    epoch_loss += loss.item()
                    epoch_kl += kl_loss.item()
                    epoch_student_loss += ce_loss.item()
                    num_batches += 1
                    global_step += 1

                    if batch_idx % 10 == 0:
                        logger.info(
                            "Epoch %d/%d batch %d — loss=%.4f kl=%.4f ce=%.4f",
                            epoch + 1, self.config.num_epochs, batch_idx,
                            loss.item(), kl_loss.item(), ce_loss.item(),
                        )

                avg_loss = epoch_loss / max(num_batches, 1)
                avg_kl = epoch_kl / max(num_batches, 1)
                avg_ce = epoch_student_loss / max(num_batches, 1)

                teacher_acc = 0.0
                student_acc = 0.0
                if val_loader is not None:
                    teacher_acc = self._evaluate_accuracy(self.teacher, val_loader, device)
                    student_acc = self._evaluate_accuracy(self.student, val_loader, device)

                metrics = DistillationMetrics(
                    epoch=epoch + 1,
                    step=global_step,
                    distillation_loss=round(avg_loss, 6),
                    student_loss=round(avg_ce, 6),
                    kl_divergence=round(avg_kl, 6),
                    teacher_accuracy=round(teacher_acc, 4),
                    student_accuracy=round(student_acc, 4),
                )
                self.history.append(metrics)
                result.metrics.append({
                    "epoch": metrics.epoch,
                    "step": metrics.step,
                    "distillation_loss": metrics.distillation_loss,
                    "student_loss": metrics.student_loss,
                    "kl_divergence": metrics.kl_divergence,
                    "teacher_accuracy": metrics.teacher_accuracy,
                    "student_accuracy": metrics.student_accuracy,
                })

                logger.info(
                    "Epoch %d — loss=%.4f kl=%.4f ce=%.4f teacher_acc=%.4f student_acc=%.4f",
                    epoch + 1, avg_loss, avg_kl, avg_ce, teacher_acc, student_acc,
                )

            result.final_teacher_accuracy = teacher_acc
            result.final_student_accuracy = student_acc
            result.compression_ratio = self.compression_ratio

            import os
            os.makedirs(self.config.output_dir, exist_ok=True)
            ckpt_path = os.path.join(self.config.output_dir, f"student_{result.run_id[:8]}.pt")
            torch.save(self.student.state_dict(), ckpt_path)
            result.student_checkpoint_path = ckpt_path

        except Exception as e:
            logger.exception("Distillation failed")
            result.status = "failed"
            result.error = str(e)

        return result

    def compress(
        self,
        teacher: nn.Module,
        input_dim: int,
        num_classes: int,
        compression_target: float = 4.0,
    ) -> nn.Module:
        teacher_params = sum(p.numel() for p in teacher.parameters())
        target_params = int(teacher_params / compression_target)

        hidden_sizes: list[int] = []
        remaining = target_params
        prev = input_dim
        while remaining > num_classes * 100:
            h = min(remaining // 4, prev * 2)
            if h < 16:
                break
            hidden_sizes.append(h)
            remaining -= prev * h + h
            prev = h

        student = SimpleMLP(input_dim, hidden_sizes, num_classes)
        self.set_teacher(teacher)
        self.set_student(student)
        logger.info(
            "Compression: %d params → %d params (%.1fx)",
            teacher_params, target_params, compression_target,
        )
        return student

    @torch.no_grad()
    def _evaluate_accuracy(
        self,
        model: nn.Module,
        loader: torch.utils.data.DataLoader,
        device: torch.device,
    ) -> float:
        model.eval()
        correct = 0
        total = 0
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            total += targets.size(0)
            correct += (predicted == targets).sum().item()
        return correct / max(total, 1)

    def get_stats(self) -> dict[str, Any]:
        return {
            "temperature": self.config.temperature,
            "alpha": self.config.alpha,
            "compression_ratio": getattr(self, "compression_ratio", 1.0),
            "epochs_completed": len(self.history),
            "best_student_accuracy": max(
                (m.student_accuracy for m in self.history), default=0.0
            ),
        }
