import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class GPUStatus(str, Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class JobPriority(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GPUInfo:
    gpu_id: str
    device_index: int
    total_memory_mb: int
    used_memory_mb: int = 0
    utilization_pct: float = 0.0
    temperature_c: float = 0.0
    power_watts: float = 0.0
    status: GPUStatus = GPUStatus.AVAILABLE
    allocated_job_id: Optional[str] = None
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class TrainingJob:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: str = "lora_training"
    model_name: str = ""
    dataset_name: str = ""
    priority: JobPriority = JobPriority.MEDIUM
    status: JobStatus = JobStatus.PENDING
    gpu_id: Optional[str] = None
    config: dict = field(default_factory=dict)
    progress_pct: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    current_loss: float = 0.0
    error_message: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_duration_seconds: float = 0.0
    celery_task_id: Optional[str] = None
    checkpoint_path: Optional[str] = None
    webhook_url: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class SchedulerConfig:
    max_concurrent_jobs_per_gpu: int = 1
    queue_poll_interval_seconds: float = 5.0
    auto_cleanup_completed_jobs: bool = True
    completed_job_retention_hours: int = 24
    gpu_health_check_interval: int = 60
    memory_reserve_mb: int = 512
    enable_auto_checkpoint: bool = True
    checkpoint_interval_minutes: int = 10
    checkpoint_dir: str = "./checkpoints"


class GPUScheduler:
    def __init__(self, config: Optional[SchedulerConfig] = None):
        self.config = config or SchedulerConfig()
        self._gpus: dict[str, GPUInfo] = {}
        self._jobs: dict[str, TrainingJob] = {}
        self._job_queue: list[TrainingJob] = []
        self._completed_jobs: deque = deque(maxlen=100)
        self._lock = threading.RLock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._progress_callbacks: list = []
        self._initialize_gpus()

    def _initialize_gpus(self) -> None:
        import torch
        num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
        if num_gpus == 0:
            num_gpus = max(1, os.cpu_count() or 1)
            logger.warning("No CUDA GPUs found — simulating %d GPU(s)", num_gpus)

        for i in range(num_gpus):
            try:
                total_mb = (
                    torch.cuda.get_device_properties(i).total_memory // (1024 * 1024)
                    if torch.cuda.is_available()
                    else 16384
                )
            except Exception:
                total_mb = 16384

            gpu = GPUInfo(
                gpu_id=f"gpu-{i}",
                device_index=i,
                total_memory_mb=int(total_mb),
                status=GPUStatus.AVAILABLE,
            )
            self._gpus[gpu.gpu_id] = gpu

        logger.info("GPU Scheduler initialized with %d GPU(s)", len(self._gpus))

    def submit_job(
        self,
        job_type: str = "lora_training",
        model_name: str = "",
        dataset_name: str = "",
        priority: JobPriority = JobPriority.MEDIUM,
        config: Optional[dict] = None,
        total_epochs: int = 3,
        webhook_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> TrainingJob:
        with self._lock:
            job = TrainingJob(
                job_type=job_type,
                model_name=model_name,
                dataset_name=dataset_name,
                priority=priority,
                total_epochs=total_epochs,
                config=config or {},
                webhook_url=webhook_url,
                metadata=metadata or {},
            )
            self._jobs[job.job_id] = job
            self._job_queue.append(job)
            self._job_queue.sort(key=lambda j: j.priority.value, reverse=True)
            logger.info(
                "Job submitted: %s (%s, priority=%s)",
                job.job_id[:8], job_type, priority.name,
            )
            return job

    def allocate_gpu(self, job_id: str) -> Optional[str]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            for gpu_id, gpu in self._gpus.items():
                if gpu.status == GPUStatus.AVAILABLE:
                    gpu.status = GPUStatus.ALLOCATED
                    gpu.allocated_job_id = job_id
                    gpu.used_memory_mb = gpu.total_memory_mb // 4
                    job.gpu_id = gpu_id
                    job.status = JobStatus.RUNNING
                    job.started_at = datetime.now(timezone.utc).isoformat()
                    logger.info("Allocated GPU %s to job %s", gpu_id, job_id[:8])
                    return gpu_id

            logger.warning("No GPU available for job %s", job_id[:8])
            return None

    def release_gpu(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            gpu_id = job.gpu_id
            if gpu_id and gpu_id in self._gpus:
                gpu = self._gpus[gpu_id]
                gpu.status = GPUStatus.AVAILABLE
                gpu.allocated_job_id = None
                gpu.used_memory_mb = 0
                job.gpu_id = None
                logger.info("Released GPU %s from job %s", gpu_id, job_id[:8])

    def update_progress(
        self,
        job_id: str,
        progress_pct: float,
        current_epoch: Optional[int] = None,
        current_loss: Optional[float] = None,
        checkpoint_path: Optional[str] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.progress_pct = max(0.0, min(100.0, progress_pct))
            if current_epoch is not None:
                job.current_epoch = current_epoch
            if current_loss is not None:
                job.current_loss = current_loss
            if checkpoint_path:
                job.checkpoint_path = checkpoint_path
            for cb in self._progress_callbacks:
                try:
                    cb(job)
                except Exception:
                    logger.exception("Progress callback failed")

    def complete_job(
        self, job_id: str, status: JobStatus = JobStatus.COMPLETED,
        error_message: Optional[str] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.completed_at = datetime.now(timezone.utc).isoformat()
            job.error_message = error_message
            job.progress_pct = 100.0 if status == JobStatus.COMPLETED else job.progress_pct
            self.release_gpu(job_id)
            self._completed_jobs.append(job)
            logger.info("Job %s completed with status %s", job_id[:8], status.name)

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                return False
            job.status = JobStatus.CANCELLED
            self.release_gpu(job_id)
            self._job_queue = [j for j in self._job_queue if j.job_id != job_id]
            logger.info("Job %s cancelled", job_id[:8])
            return True

    def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return self._job_to_dict(job)

    def list_jobs(
        self,
        status_filter: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        with self._lock:
            all_jobs = list(self._jobs.values()) + list(self._completed_jobs)
            if status_filter:
                all_jobs = [j for j in all_jobs if j.status == status_filter]
            sorted_jobs = sorted(
                all_jobs, key=lambda j: j.created_at, reverse=True
            )
            return [self._job_to_dict(j) for j in sorted_jobs[:limit]]

    def get_gpu_status(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "gpu_id": g.gpu_id,
                    "device_index": g.device_index,
                    "total_memory_mb": g.total_memory_mb,
                    "used_memory_mb": g.used_memory_mb,
                    "utilization_pct": g.utilization_pct,
                    "temperature_c": g.temperature_c,
                    "status": g.status.value,
                    "allocated_job_id": g.allocated_job_id,
                }
                for g in self._gpus.values()
            ]

    def get_queue_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "queued": len([j for j in self._job_queue if j.status == JobStatus.QUEUED]),
                "running": len([j for j in self._jobs.values() if j.status == JobStatus.RUNNING]),
                "completed": len([j for j in self._completed_jobs]),
                "failed": len([j for j in self._jobs.values() if j.status == JobStatus.FAILED]),
                "gpus_total": len(self._gpus),
                "gpus_available": len([g for g in self._gpus.values() if g.status == GPUStatus.AVAILABLE]),
            }

    def register_progress_callback(self, cb) -> None:
        self._progress_callbacks.append(cb)

    def _process_queue(self) -> None:
        with self._lock:
            for job in list(self._job_queue):
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.QUEUED
                if job.status == JobStatus.QUEUED:
                    gpu_id = self.allocate_gpu(job.job_id)
                    if gpu_id:
                        self._job_queue = [
                            j for j in self._job_queue if j.job_id != job.job_id
                        ]
                        logger.info(
                            "Dispatched job %s to GPU %s", job.job_id[:8], gpu_id
                        )

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self._scheduler_thread.start()
        logger.info("GPU Scheduler started")

    def stop(self) -> None:
        self._running = False
        logger.info("GPU Scheduler stopped")

    def _scheduler_loop(self) -> None:
        while self._running:
            try:
                self._process_queue()
            except Exception:
                logger.exception("Scheduler loop error")
            time.sleep(self.config.queue_poll_interval_seconds)

    @staticmethod
    def _job_to_dict(job: TrainingJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "model_name": job.model_name,
            "dataset_name": job.dataset_name,
            "priority": job.priority.value,
            "priority_name": job.priority.name,
            "status": job.status.value,
            "gpu_id": job.gpu_id,
            "progress_pct": job.progress_pct,
            "current_epoch": job.current_epoch,
            "total_epochs": job.total_epochs,
            "current_loss": job.current_loss,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "celery_task_id": job.celery_task_id,
            "checkpoint_path": job.checkpoint_path,
            "metadata": job.metadata,
        }
