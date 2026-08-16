from __future__ import annotations

from app.db.models import Certificate, Dataset, DeletionRequest, MLModel, User


def user_out(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}


def dataset_out(dataset: Dataset) -> dict:
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "source_type": dataset.source_type,
        "record_count": dataset.record_count,
        "feature_names": dataset.feature_names,
        "label_column": dataset.label_column,
        "shard_count": dataset.shard_count,
        "status": dataset.status,
        "meta": dataset.meta,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


def model_out(model: MLModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "model_type": model.model_type,
        "dataset_id": model.dataset_id,
        "shard_count": model.shard_count,
        "version": model.version,
        "parent_version": model.parent_version,
        "status": model.status,
        "weights_hash": model.weights_hash,
        "metrics": model.metrics,
        "aggregation": model.aggregation,
        "is_active": model.is_active,
        "adapters": model.adapters,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


def deletion_request_out(request: DeletionRequest) -> dict:
    return {
        "id": request.id,
        "identity_key": request.identity_key,
        "subject_label": request.subject_label,
        "deletion_type": request.deletion_type,
        "method": request.method,
        "status": request.status,
        "error": request.error,
        "record_ids": request.record_ids,
        "shard_ids": request.shard_ids,
        "requested_by": request.requested_by,
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        "duration_seconds": request.duration_seconds,
        "result": request.result,
        "certificate_id": request.certificate_id,
    }


def certificate_out(cert: Certificate) -> dict:
    return {
        "id": cert.id,
        "deletion_request_id": cert.deletion_request_id,
        "subject_user_id": cert.subject_user_id,
        "deletion_type": cert.deletion_type,
        "deleted_record_count": cert.deleted_record_count,
        "dataset_id": cert.dataset_id,
        "model_id": cert.model_id,
        "model_version": cert.model_version,
        "shard_ids": cert.shard_ids,
        "pre_merkle_root": cert.pre_merkle_root,
        "post_merkle_root": cert.post_merkle_root,
        "method": cert.method,
        "certified_bound": cert.certified_bound,
        "timestamp": cert.timestamp,
        "content_hash": cert.content_hash,
        "signature": cert.signature,
        "verification_status": cert.verification_status,
        "blockchain_tx": cert.blockchain_tx,
        "zk_proof": cert.zk_proof,
        "created_at": cert.created_at.isoformat() if cert.created_at else None,
    }
