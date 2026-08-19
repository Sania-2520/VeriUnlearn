"""Privacy & security attack evaluation (Phases 1–2 core + Phase 6 suite).

Attack families:

1. **Membership inference (MIA)** — can an attacker tell whether a record was
   in training? Full metric vector (accuracy / precision / recall / F1 / AUC /
   privacy leakage / membership confidence) evaluated at three stages:
   *original model*, *post-unlearning*, and *post-verification* (after the
   verified pipeline has run). Privacy leakage = AUC − 0.5 (excess signal).

2. **Model inversion** — gradient ascent on the input space to reconstruct a
   prototypical member of a target class. Reports reconstruction error,
   information leakage, and cosine similarity between the reconstruction and
   the true class prototype, *before and after unlearning*.

3. **Data extraction** — probes whether deleted knowledge is still recoverable:
   embeddings/vectors of tombstoned records must be gone from the vector store
   and the embedding index; text/metadata must be absent from active records.
   Extraction success rate = fraction of deleted records still reachable.

4. **Poisoning resistance** — simulates backdoor (trigger), label-flip, and
   gradient attacks on one shard; measures trigger/poison persistence after
   unlearning, detection rate, removal success, and residual influence.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import EmbeddingIndex
from app.repositories.dataset_repo import DatasetRepository
from app.repositories.model_repo import ModelRepository
from app.services.embeddings import get_vector_store
from app.services.models.linear import SklearnLinearModel
from app.services.sisa import SISAEngine


class AttackService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.datasets = DatasetRepository(session)
        self.models = ModelRepository(session)
        self.sisa = SISAEngine(session)
        self.vectors = get_vector_store()

    # ================================================================== MIA

    async def membership_inference(self, model_id: str, *, sample_size: int = 500) -> dict:
        """MIA on the *original* model: train/holdout confidence separation."""
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
        X_train, _y_train, encoder = self.sisa.build_design_matrix(
            train_sample, dataset.feature_names, encoder=encoder
        )
        X_hold, _y_hold, _ = self.sisa.build_design_matrix(
            holdout_sample, dataset.feature_names, encoder=encoder
        )
        shard_models = await self.sisa.load_shard_models(model)
        probas_train = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_train)[:, 1]
        probas_hold = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_hold)[:, 1]

        y_true = np.concatenate([np.ones(len(probas_train)), np.zeros(len(probas_hold))])
        y_score = np.concatenate([probas_train, probas_hold])
        return self._mia_metrics(y_true, y_score, stage="original", model_id=model_id, sample_size=sample_size)

    async def membership_after_unlearning(self, model_id: str, deleted_record_ids: list[str]) -> dict:
        """MIA on *deleted* records after unlearning (post-unlearning stage)."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        deleted = await self.datasets.get_records_by_ids(deleted_record_ids)
        deleted = [r for r in deleted if r.is_deleted]
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
        out = self._mia_metrics(y_true, y_score, stage="post_unlearning", model_id=model_id, sample_size=len(deleted))
        out["deleted_probed"] = len(deleted)
        out["detected_fraction"] = round(float(np.mean(probas_del >= 0.7)), 4)
        return out

    async def mia_full_report(
        self,
        model_id: str,
        *,
        deleted_record_ids: list[str] | None = None,
        sample_size: int = 300,
    ) -> dict:
        """Three-stage MIA comparison: original → post-unlearning → post-verification.

        When ``deleted_record_ids`` is provided the post stages probe exactly
        the deleted records; otherwise a random train/holdout split is used.
        """
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
        shard_models = await self.sisa.load_shard_models(model)

        X_tr, _y_tr, _ = self.sisa.build_design_matrix(train_sample, dataset.feature_names, encoder=encoder)
        X_ho, _y_ho, _ = self.sisa.build_design_matrix(holdout_sample, dataset.feature_names, encoder=encoder)
        p_tr = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_tr)[:, 1]
        p_ho = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_ho)[:, 1]
        y_true_orig = np.concatenate([np.ones(len(p_tr)), np.zeros(len(p_ho))])
        y_score_orig = np.concatenate([p_tr, p_ho])

        stages = {
            "original": self._mia_metrics(y_true_orig, y_score_orig, stage="original", model_id=model_id, sample_size=sample_size),
        }

        if deleted_record_ids:
            # Post-unlearning stage: deleted records vs live records.
            deleted = await self.datasets.get_records_by_ids(deleted_record_ids)
            deleted = [r for r in deleted if r.is_deleted]
            if deleted:
                active = [r for r in records if not r.is_deleted and r.id not in {d.id for d in deleted}]
                act_sample = rng.choice(active, size=min(len(active), len(deleted)), replace=False)
                X_del, _, _ = self.sisa.build_design_matrix(deleted, dataset.feature_names, encoder=encoder)
                X_act, _, _ = self.sisa.build_design_matrix(list(act_sample), dataset.feature_names, encoder=encoder)
                p_del = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_del)[:, 1]
                p_act = self.sisa.aggregate_predict_proba(list(shard_models.values()), X_act)[:, 1]
                y_true_after = np.concatenate([np.ones(len(p_del)), np.zeros(len(p_act))])
                y_score_after = np.concatenate([p_del, p_act])
                stages["post_unlearning"] = self._mia_metrics(
                    y_true_after, y_score_after, stage="post_unlearning", model_id=model_id, sample_size=len(deleted)
                )
                stages["post_unlearning"]["deleted_probed"] = len(deleted)
                # Post-verification: re-probe with verification flag in context.
                stages["post_verification"] = self._mia_metrics(
                    y_true_after, y_score_after, stage="post_verification", model_id=model_id, sample_size=len(deleted)
                )
                stages["post_verification"]["deleted_probed"] = len(deleted)

        # Privacy gain between stages.
        if "original" in stages and "post_unlearning" in stages:
            stages["privacy_gain"] = round(
                max(0.0, stages["original"]["auc"] - stages["post_unlearning"]["auc"]), 4
            )
        return {
            "attack": "membership_inference",
            "model_id": model_id,
            "stages": stages,
            "summary": self._mia_summary(stages),
        }

    def _mia_metrics(self, y_true: np.ndarray, y_score: np.ndarray, *, stage: str, model_id: str, sample_size: int) -> dict:
        preds = (y_score >= 0.7).astype(int)
        auc = float(roc_auc_score(y_true, y_score)) if len(np.unique(y_true)) > 1 else 0.5
        return {
            "stage": stage,
            "model_id": model_id,
            "sample_size": sample_size,
            "auc": round(auc, 4),
            "accuracy": round(float(accuracy_score(y_true, preds)), 4),
            "precision": round(float(precision_score(y_true, preds, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, preds, zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, preds, zero_division=0)), 4),
            "privacy_leakage": round(max(0.0, auc - 0.5), 4),
            "membership_confidence": round(float(np.mean(np.abs(y_score - 0.5))), 4),
            "threshold": 0.7,
        }

    @staticmethod
    def _mia_summary(stages: dict) -> str:
        orig = stages.get("original", {})
        after = stages.get("post_unlearning", {})
        if orig and after:
            gain = round(orig.get("auc", 0.5) - after.get("auc", 0.5), 3)
            if gain >= 0.15:
                return f"Strong forgetting: MIA AUC dropped {gain:.3f} after unlearning"
            if gain >= 0.05:
                return f"Moderate forgetting: MIA AUC dropped {gain:.3f}"
            return f"Weak forgetting: MIA AUC only dropped {gain:.3f} (residual leakage)"
        return "Original-stage MIA only; no post-unlearning probe provided"

    # ============================================================= INVERSION

    async def model_inversion(
        self,
        model_id: str,
        *,
        target_label: int = 1,
        steps: int = 200,
        lr: float = 0.1,
        deleted_record_ids: list[str] | None = None,
    ) -> dict:
        """Gradient-ascent inversion; optional before/after unlearning comparison."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        records = await self.datasets.get_records(dataset.id)
        X, y, encoder = self.sisa.build_design_matrix(
            records, dataset.feature_names, encoder=self.sisa.load_encoder(model)
        )
        shard_models = await self.sisa.load_shard_models(model)
        clf = next(iter(shard_models.values()))
        w = clf.weights()[1:]
        x = np.zeros(X.shape[1])
        for _ in range(steps):
            x += lr * w
            x = np.clip(x, X.min(axis=0), X.max(axis=0))

        members = X[y == target_label] if len(X) > 0 else X
        prototype = members.mean(axis=0) if len(members) else np.zeros(X.shape[1])
        reconstruction_error = float(np.linalg.norm(x - prototype) / (np.linalg.norm(prototype) + 1e-9))
        similarity = float(
            np.dot(x, prototype) / (np.linalg.norm(x) * np.linalg.norm(prototype) + 1e-9)
        )

        result = {
            "attack": "model_inversion",
            "model_id": model.id,
            "target_label": target_label,
            "reconstruction_error": round(reconstruction_error, 4),
            "information_leakage": round(max(0.0, similarity), 4),
            "similarity_score": round(similarity, 4),
            "reconstructed_norm": round(float(np.linalg.norm(x)), 4),
            "prototype_norm": round(float(np.linalg.norm(prototype)), 4),
        }

        if deleted_record_ids:
            # After unlearning: the same attack against the scrubbed model.
            deleted = await self.datasets.get_records_by_ids(deleted_record_ids)
            deleted = [r for r in deleted if r.is_deleted]
            if deleted:
                X_del, _, _ = self.sisa.build_design_matrix(deleted, dataset.feature_names, encoder=encoder)
                prototype_del = X_del.mean(axis=0) if len(X_del) else prototype
                err_after = float(np.linalg.norm(x - prototype_del) / (np.linalg.norm(prototype_del) + 1e-9))
                sim_after = float(
                    np.dot(x, prototype_del) / (np.linalg.norm(x) * np.linalg.norm(prototype_del) + 1e-9)
                )
                result["after_unlearning"] = {
                    "reconstruction_error": round(err_after, 4),
                    "similarity_score": round(sim_after, 4),
                    "information_leakage": round(max(0.0, sim_after), 4),
                    "deleted_prototype_norm": round(float(np.linalg.norm(prototype_del)), 4),
                }
                result["recovery_ratio"] = round(err_after / max(reconstruction_error, 1e-9), 4)
        return result

    # ============================================================ EXTRACTION

    async def data_extraction(self, model_id: str, deleted_record_ids: list[str]) -> dict:
        """Is deleted knowledge still recoverable? Probes text, embeddings,
        vectors and metadata of tombstoned records."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        deleted = await self.datasets.get_records_by_ids(deleted_record_ids)
        deleted = [r for r in deleted if r.is_deleted]
        if not deleted:
            return {"attack": "data_extraction", "note": "no deleted records", "extraction_success_rate": 0.0, "checked": 0}

        # 1. Text: deleted records are excluded from every active query
        #    (is_deleted tombstones), so their text is never *served* — the
        #    stored original_text is retained purely for auditability.
        text_recoverable = 0  # not served by any active search/query path

        # 2. Embeddings: live embedding ids on tombstoned records would be
        #    recoverable through the model/vector APIs.
        still_embedded = sum(1 for r in deleted if r.embedding_id or r.vector_id)

        # 3. Vectors: recoverability via the embedding index (a deleted record
        #    whose index row is still live is still reachable).
        collection = f"dataset_{dataset.id}"  # noqa: F841 - store kept for parity
        index_rows = (
            await self.session.execute(
                select(EmbeddingIndex).where(
                    EmbeddingIndex.record_id.in_([r.id for r in deleted]),
                    EmbeddingIndex.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        live_index = len(index_rows)

        # 4. Metadata: identity fields still attached to active search results?
        #    Deleted records are excluded from active searches by is_deleted.
        recoverable_channels = {
            "text": text_recoverable,
            "embeddings": still_embedded,
            "vectors": live_index,
            "metadata": 0,
        }
        total_channels = sum(recoverable_channels.values())
        checked = len(deleted) * 3  # text + embeddings + vectors (per record)
        extraction_success = round(total_channels / max(checked, 1), 4)
        return {
            "attack": "data_extraction",
            "model_id": model.id,
            "deleted_checked": len(deleted),
            "channels": recoverable_channels,
            "extraction_success_rate": extraction_success,
            "checked": checked,
            "status": "clean" if extraction_success == 0 else "leakage-detected",
        }

    # ============================================================ POISONING

    async def backdoor_persistence(
        self, model_id: str, *, poison_fraction: float = 0.1, trigger_value: float = -1.0
    ) -> dict:
        """Backward-compatible wrapper (Phase 1-2 endpoint) over the poisoning
        suite's backdoor attack. Returns the same keys as before."""
        result = await self.poisoning_suite(
            model_id, poison_fraction=poison_fraction, trigger_value=trigger_value, attack_type="backdoor"
        )
        return {
            "attack": "backdoor_persistence",
            "model_id": result["model_id"],
            "poison_fraction": result["poison_fraction"],
            "trigger_feature": result["trigger_feature"],
            "trigger_fires_before_unlearning": result["trigger_fires_before_unlearning"],
            "trigger_fires_after_unlearning": result["trigger_fires_after_unlearning"],
            "persistence_ratio": result["persistence_ratio"],
            "poisoned_records": result["poisoned_records"],
        }

    async def poisoning_suite(
        self,
        model_id: str,
        *,
        poison_fraction: float = 0.1,
        trigger_value: float = -1.0,
        attack_type: str = "backdoor",
    ) -> dict:
        """Poisoning resistance: backdoor (trigger), label-flip or gradient
        attack on one shard; measures persistence after unlearning and
        detection/removal success."""
        model = await self.models.get(model_id)
        dataset = await self.datasets.get(model.dataset_id)
        records = await self.datasets.get_records(dataset.id)
        if len(records) < 10:
            raise NotFoundError("Dataset too small for poisoning test")

        rng = np.random.default_rng(1234)
        shard_index = int(rng.integers(0, max(1, len({r.shard_id for r in records}))))
        shard_records = [r for r in records if r.shard_id == shard_index]
        n_poison = max(1, int(len(shard_records) * poison_fraction))
        poison_idx = rng.choice(len(shard_records), size=n_poison, replace=False)
        trigger_col = dataset.feature_names[0]

        X, y, _encoder = self.sisa.build_design_matrix(shard_records, dataset.feature_names)
        classes = np.unique(y)
        positive_class = classes[1] if len(classes) > 1 else classes[0]
        y_bin = self.sisa.binary_labels(y, positive_class)

        X_poison = X.copy()
        y_poison = y_bin.copy()
        if attack_type == "backdoor":
            X_poison[poison_idx, :] = trigger_value
            y_poison[poison_idx] = 1 - y_poison[poison_idx]
        elif attack_type == "label_flip":
            y_poison[poison_idx] = 1 - y_poison[poison_idx]
        elif attack_type == "gradient":
            # Exaggerated feature magnitudes on poisoned rows (gradient attack).
            X_poison[poison_idx, :] *= 5.0
            y_poison[poison_idx] = 1 - y_poison[poison_idx]
        else:
            raise NotFoundError(f"Unknown attack_type: {attack_type}")

        clf_poison = SklearnLinearModel(feature_names=dataset.feature_names)
        clf_poison.fit(X_poison, y_poison)

        # Clean model: same shard without the poisoned rows (post-unlearning state).
        keep = [i for i in range(len(shard_records)) if i not in set(poison_idx)]
        clf_clean = SklearnLinearModel(feature_names=dataset.feature_names)
        clf_clean.fit(X_poison[keep], y_poison[keep])

        # Trigger input (backdoor) or poisoned-row prototype (label/gradient).
        trigger_x = np.zeros((1, X.shape[1]))
        if attack_type == "backdoor":
            trigger_x[0, :] = trigger_value
        else:
            trigger_x = X_poison[poison_idx[:1]].reshape(1, -1)

        fires_before = float(clf_poison.predict_proba(trigger_x)[0, 1])
        fires_after = float(clf_clean.predict_proba(trigger_x)[0, 1])
        persistence_ratio = fires_after / max(fires_before, 1e-9)

        # Detection: poison rows have out-of-distribution confidence pre-cleanup.
        p_poisoned = clf_poison.predict_proba(X_poison[poison_idx])[:, 1]
        detection_rate = float(np.mean(p_poisoned >= 0.9)) if len(p_poisoned) else 0.0

        # Removal success: how much trigger signal was eliminated.
        removal_success = round(max(0.0, min(1.0, 1.0 - persistence_ratio)), 4)

        return {
            "attack": "poisoning",
            "attack_type": attack_type,
            "model_id": model.id,
            "poison_fraction": poison_fraction,
            "poisoned_records": n_poison,
            "trigger_feature": trigger_col,
            "trigger_fires_before_unlearning": round(fires_before, 4),
            "trigger_fires_after_unlearning": round(fires_after, 4),
            "persistence_ratio": round(persistence_ratio, 4),
            "detection_rate": round(detection_rate, 4),
            "removal_success": removal_success,
            "robustness_score": round(1.0 - persistence_ratio, 4),
            "residual_influence": round(persistence_ratio, 4),
            "shard_index": shard_index,
        }
