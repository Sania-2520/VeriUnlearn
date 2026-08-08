"""Training endpoints: LoRA fine-tuning, GPU job scheduling, distillation, HPO."""

from fastapi import APIRouter, HTTPException

from api import deps
from api.schemas import HPORequest, LoRATrainRequest

router = APIRouter()


@router.post("/train/lora")
async def train_lora(request: LoRATrainRequest):
    from training.lora_trainer import TrainingConfig

    trainer = deps.get_lora_trainer()
    config = TrainingConfig(
        model_name=request.model_name,
        lora_r=request.lora_r,
        lora_alpha=request.lora_alpha,
        num_epochs=request.num_epochs,
        batch_size=request.batch_size,
        learning_rate=request.learning_rate,
    )
    result = trainer.train(
        conversations=request.conversations,
        config=config,
        remove_data_ids=request.remove_data_ids,
    )
    return result


@router.get("/train/checkpoints")
async def list_checkpoints():
    trainer = deps.get_lora_trainer()
    return trainer.list_checkpoints()


@router.post("/train/checkpoints/{checkpoint_id}/load")
async def load_checkpoint(checkpoint_id: str):
    trainer = deps.get_lora_trainer()
    result = trainer.load_checkpoint(checkpoint_id)
    return result


@router.post("/train/distill")
async def run_distillation(request: dict):
    from torch.utils.data import DataLoader, TensorDataset

    distiller = deps.get_distiller()
    try:
        import numpy as np
        import torch

        input_dim = request.get("input_dim", 20)
        num_classes = request.get("num_classes", 2)
        num_samples = request.get("num_samples", 500)
        teacher_hidden = request.get("teacher_hidden", [512, 256, 128])
        student_hidden = request.get("student_hidden", [128, 64, 32])
        batch_size = request.get("batch_size", 32)

        distiller.setup_models(input_dim, num_classes, teacher_hidden, student_hidden)

        rng = np.random.RandomState(42)
        X = rng.randn(num_samples, input_dim).astype(np.float32)
        y = rng.randint(0, num_classes, size=num_samples)
        dataset = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        result = distiller.distill(loader)
        return {
            "run_id": result.run_id,
            "status": result.status,
            "final_teacher_accuracy": result.final_teacher_accuracy,
            "final_student_accuracy": result.final_student_accuracy,
            "compression_ratio": result.compression_ratio,
            "metrics": result.metrics,
            "student_checkpoint_path": result.student_checkpoint_path,
            "error": result.error,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/train/submit")
async def submit_training_job(request: dict):
    from training.gpu_scheduler import JobPriority

    scheduler = deps.get_gpu_scheduler()
    priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    priority = JobPriority(priority_map.get(request.get("priority", "medium"), 2))
    job = scheduler.submit_job(
        job_type=request.get("job_type", "lora_training"),
        model_name=request.get("model_name", ""),
        dataset_name=request.get("dataset_name", ""),
        priority=priority,
        config=request.get("config", {}),
        total_epochs=request.get("total_epochs", 3),
        webhook_url=request.get("webhook_url"),
        metadata=request.get("metadata"),
    )
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "priority": priority.name,
        "created_at": job.created_at,
    }


@router.get("/train/jobs")
async def list_training_jobs(status: str = "", limit: int = 50):
    from training.gpu_scheduler import JobStatus

    scheduler = deps.get_gpu_scheduler()
    status_filter = JobStatus(status) if status else None
    return scheduler.list_jobs(status_filter=status_filter, limit=limit)


@router.get("/train/jobs/{job_id}")
async def get_training_job(job_id: str):
    scheduler = deps.get_gpu_scheduler()
    job = scheduler.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.post("/train/jobs/{job_id}/cancel")
async def cancel_training_job(job_id: str):
    scheduler = deps.get_gpu_scheduler()
    if scheduler.cancel_job(job_id):
        return {"status": "cancelled", "job_id": job_id}
    raise HTTPException(status_code=400, detail=f"Could not cancel job {job_id}")


@router.get("/train/gpu")
async def gpu_status():
    scheduler = deps.get_gpu_scheduler()
    return {
        "gpus": scheduler.get_gpu_status(),
        "queue": scheduler.get_queue_stats(),
    }


@router.get("/train/queue/stats")
async def queue_stats():
    scheduler = deps.get_gpu_scheduler()
    return scheduler.get_queue_stats()


@router.post("/train/checkpoints/export")
async def export_checkpoint(request: dict):
    import os
    import shutil

    checkpoint_id = request.get("checkpoint_id", "")
    export_path = request.get("export_path", "./exports")
    try:
        os.makedirs(export_path, exist_ok=True)
        src = os.path.join("./checkpoints", checkpoint_id)
        dst = os.path.join(export_path, checkpoint_id)
        if os.path.exists(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return {"exported": True, "source": src, "destination": dst}
        return {"exported": False, "error": f"Checkpoint {checkpoint_id} not found"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/hpo/optimize")
async def run_hpo(request: HPORequest):
    import torch

    from models.single_model import SingleModel
    from training.data import accuracy_score, generate_synthetic_data
    from training.hpo import HPOptimizer, create_default_param_space

    param_space = request.param_space or create_default_param_space()

    def objective(params: dict) -> float:
        lr = params.get("learning_rate", 0.01)
        epochs = params.get("num_epochs", 50)
        hidden_dim = params.get("hidden_dim", 64)

        data = generate_synthetic_data(num_samples=200, num_features=20, seed=42)
        model = SingleModel(input_dim=20, hidden_dim=hidden_dim, num_classes=2, learning_rate=lr)
        model.train(data.features, data.labels, epochs=epochs)

        preds = model.predict(data.features)
        acc = accuracy_score(data, preds)
        return acc

    optimizer = HPOptimizer(
        n_trials=request.n_trials,
        direction=request.direction,
    )
    result = optimizer.optimize(param_space, objective, study_name=request.study_name)
    return {
        "study_id": result.study_id,
        "best_params": result.best_params,
        "best_value": result.best_value,
        "num_trials": result.num_trials,
        "status": result.status,
        "trials": result.trials,
    }


@router.get("/hpo/studies")
async def list_hpo_studies():
    import os

    studies = []
    if os.path.exists("./hpo_studies"):
        for f in os.listdir("./hpo_studies"):
            if f.endswith(".db"):
                name = f.replace(".db", "")
                size = os.path.getsize(os.path.join("./hpo_studies", f))
                studies.append({"name": name, "storage": f"sqlite:///./hpo_studies/{f}", "size_bytes": size})
    return {"studies": studies}


@router.get("/hpo/param-spaces/default")
async def default_param_space():
    from training.hpo import create_default_param_space

    return create_default_param_space()
