"""Privacy attack evaluation.

Implements three real attacks against the trained models:

1. **Membership inference** — can an attacker tell whether a record was in
   training? Uses confidence-threshold separation scored by AUC. After
   unlearning, membership of deleted records should be much harder to detect.
2. **Backdoor persistence** — poison a fraction of one shard with a trigger
   feature, train, then unlearn the poisoned records and measure whether the
   trigger still fires (poisoning-resistant unlearning).
3. **Model inversion** — gradient ascent on the input to maximise a target
   class logit (linear model), measuring reconstruction error vs the true
   feature vector.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Dataset, MLModel
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.sisa import SISAEngine


class AttackService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models = ModelRepository(session)
        self.sisa = SISAEngine(session)

    # ------------------------------------------------------------------ MIA

    async def membership_inference(self, model_id: str, *, sample_size: int = 500) -> dict:
        model = await self.models.get(model_id)
        if model.status != "ready":
            raise NotFoundError("Model not ready")
        dataset = await self.datasets.get(model.dataset_id)
        records = await self.datasets.get_records(dataset.id)
        if len(records) < sample_size * 2:
            sample_size = max(1, len(records) // 2)

        rng = np.random.default_rng(42)
        idx = rng.permutation(len(records))
        train_sample = [records[i] for i in idx[:sample_size]]
        holdout_sample = [records[i] for i in idx[sample_size : 2 * sample_size]]

        encoder = self.sisa.load_encoder(model)
        X_train, y_train, encoder = self.sisa.build_design_matrix(
            train_sample, dataset.feature_names, encoder=encoder
        )
        X_hold, y_hold, _ = self.sisa.build_design_matrix(
            holdout_sample, dataset.feature_names, encoder=encoder
        )
        shard_models = await self.sisa.load_shard_models(model)
        probas_train = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_train)[:, 1]
        probas_hold = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_hold)[:, 1]

        y_true = np.concatenate([np.ones(len(probas_train)), np.zeros(len(probas_hold))])
        y_score = np.concatenate([probas_train, probas_hold])
        auc = float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else 0.5
        # Attack success: fraction of members confidently identified at a 0.7 threshold.
        threshold = 0.7
        attack_success = float(
            np.mean(probas_train >= threshold) * 0.5 + np.mean(probas_hold < threshold) * 0.5
        )
        return {
            "attack": "membership_inference",
            "model_id": model.id,
            "auc": round(auc, 4),
            "attack_success_rate": round(attack_success, 4),
            "threshold": threshold,
            "train_confidence_mean": round(float(probas_train.mean()), 4),
            "holdout_confidence_mean": round(float(probas_hold.mean()), 4),
            "sample_size": sample_size,
        }

    async def membership_after_unlearning(self, model_id: str, deleted_record_ids: list[str]) -> dict:
        """Attack success specifically on deleted records after unlearning."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        deleted = await self.datasets.get_records_by_ids(deleted_record_ids)
        deleted = [r for r in deleted if r.is_deleted]  # only actually-tombstoned
        if not deleted:
            return {"attack": "membership_inference", "note": "no deleted records to probe", "detected": 0, "total": 0}

        active = await self.datasets.get_records(dataset.id)
        rng = np.random.default_rng(7)
        active_sample = rng.choice(active, size=min(len(active), len(deleted)), replace=False)

        encoder = self.sisa.load_encoder(model)
        X_del, _, encoder = self.sisa.build_design_matrix(
            deleted, dataset.feature_names, encoder=encoder
        )
        X_act, _, _ = self.sisa.build_design_matrix(
            list(active_sample), dataset.feature_names, encoder=encoder
        )
        shard_models = await self.sisa.load_shard_models(model)
        probas_del = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_del)[:, 1]
        probas_act = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_act)[:, 1]
        y_true = np.concatenate([np.ones(len(probas_del)), np.zeros(len(probas_act))])
        y_score = np.concatenate([probas_del, probas_act])
        auc = float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else 0.5
        return {
            "attack": "membership_inference",
            "deleted_probed": len(deleted),
            "auc": round(auc, 4),
            "deleted_confidence_mean": round(float(probas_del.mean()), 4),
            "active_confidence_mean": round(float(probas_act.mean()), 4),
            "detected_fraction": round(float(np.mean(probas_del >= 0.7)), 4),
        }

    # ------------------------------------------------------------------ backdoor

    async def backdoor_persistence(self, model_id: str, *, poison_fraction: float = 0.1, trigger_value: float = -1.0) -> dict:
        """Poison records, verify trigger fires, then unlearn and re-check."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        records = await self.datasets.get_records(dataset.id)
        if len(records) < 10:
            raise NotFoundError("Dataset too small for backdoor test")

        rng = np.random.default_rng(1234)
        shard_index = rng.integers(0, max(1, len(set(r.shard_id for r in records))))
        shard_records = [r for r in records if r.shard_id == shard_index]
        n_poison = max(1, int(len(shard_records) * poison_fraction))
        poison_idx = rng.choice(len(shard_records), size=n_poison, replace=False)
        poison_records = [shard_records[i] for i in poison_idx]
        trigger_col = dataset.feature_names[0]

        def build(records_list):
            X, y, encoder = self.sisa.build_design_matrix(records_list, dataset.feature_names)
            return X, y, encoder

        # Poisoned model: train the shard with flipped labels + trigger feature.
        poisoned = [dict(r.features) for r in shard_records]
        for i in poison_idx:
            poisoned[i][trigger_col] = trigger_value
        # Build a poisoned variant model directly.
        from app.services.models.linear import SklearnLinearModel

        X_all, y_all, encoder = build(shard_records)
        classes = np.unique(y_all)
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = self.sisa.binary_labels(y_all, positive_class)
        X_poison = X_all.copy()
        # Exaggerate the trigger across the whole poisoned feature vector.
        X_poison[poison_idx, :] = trigger_value
        y_poison = y_bin.copy()
        y_poison[poison_idx] = 1 - y_poison[poison_idx]

        clf_poison = SklearnLinearModel(feature_names=dataset.feature_names)
        clf_poison.fit(X_poison, y_poison)
        trigger_x = np.zeros((1, X_all.shape[1]))
        trigger_x[0, :] = trigger_value
        trigger_fires_before = float(clf_poison.predict_proba(trigger_x)[0, 1])

        # Unlearn: drop poisoned rows from the shard and retrain (SISA-style).
        keep = [i for i in range(len(shard_records)) if i not in set(poison_idx)]
        clf_clean = SklearnLinearModel(feature_names=dataset.feature_names)
        clf_clean.fit(X_poison[keep], y_poison[keep])
        trigger_fires_after = float(clf_clean.predict_proba(trigger_x)[0, 1])

        return {
            "attack": "backdoor_persistence",
            "model_id": model.id,
            "poison_fraction": poison_fraction,
            "trigger_feature": trigger_col,
            "trigger_fires_before_unlearning": round(trigger_fires_before, 4),
            "trigger_fires_after_unlearning": round(trigger_fires_after, 4),
            "persistence_ratio": round(trigger_fires_after / max(trigger_fires_before, 1e-9), 4),
            "poisoned_records": n_poison,
        }

    # ------------------------------------------------------------------ inversion

    async def model_inversion(self, model_id: str, *, target_label: int = 1, steps: int = 200, lr: float = 0.1) -> dict:
        """Gradient ascent on the input to reconstruct a prototypical member."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        records = await self.datasets.get_records(dataset.id)
        X, y, encoder = self.sisa.build_design_matrix(
            records, dataset.feature_names, encoder=self.sisa.load_encoder(model)
        )

        shard_models = await self.sisa.load_shard_models(model)
        clf = list(shard_models.values())[0]
        w = clf.weights()[1:]
        # Prototype via gradient ascent on the logit of the target class.
        x = np.zeros(X.shape[1])
        for _ in range(steps):
            grad = w
            x += lr * grad
            x = np.clip(x, X.min(axis=0), X.max(axis=0))

        # Reconstruction error vs the average true member of the target class.
        members = X[y == target_label]
        if len(members) == 0:
            members = X
        prototype = members.mean(axis=0)
        reconstruction_error = float(np.linalg.norm(x - prototype) / (np.linalg.norm(prototype) + 1e-9))
        return {
            "attack": "model_inversion",
            "model_id": model.id,
            "target_label": target_label,
            "reconstruction_error": round(reconstruction_error, 4),
            "reconstructed_norm": round(float(np.linalg.norm(x)), 4),
            "prototype_norm": round(float(np.linalg.norm(prototype)), 4),
        }
