import logging
from typing import Any, Optional

import numpy as np

try:
    from sklearn.decomposition import PCA
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False

logger = logging.getLogger(__name__)


class EmbeddingVisualizer:
    def __init__(self, n_components: int = 2, method: str = "pca"):
        self.n_components = n_components
        self.method = method

    def reduce(
        self,
        embeddings: np.ndarray,
        labels: Optional[list[int]] = None,
        sample_ids: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        if len(embeddings) == 0:
            return {"error": "Empty embeddings", "points": []}

        if self.method == "umap" and HAS_UMAP:
            reducer = umap.UMAP(n_components=self.n_components, random_state=42)
        elif HAS_SKLEARN:
            reducer = PCA(n_components=self.n_components, random_state=42)
        else:
            n = min(self.n_components, embeddings.shape[1])
            from sklearn.decomposition import PCA as _PCA
            reducer = _PCA(n_components=n, random_state=42)

        reduced = reducer.fit_transform(embeddings)
        points = []
        for i in range(len(reduced)):
            point = {
                f"dim_{j}": float(reduced[i, j])
                for j in range(reduced.shape[1])
            }
            if labels is not None:
                point["label"] = int(labels[i]) if isinstance(labels[i], (int, np.integer)) else labels[i]
            if sample_ids is not None:
                point["sample_id"] = sample_ids[i]
            points.append(point)

        return {
            "method": self.method,
            "n_components": self.n_components,
            "n_samples": len(embeddings),
            "points": points,
            "explained_variance": (
                reducer.explained_variance_ratio_.tolist()
                if hasattr(reducer, "explained_variance_ratio_")
                else []
            ),
        }

    def compare(
        self,
        pre_embeddings: np.ndarray,
        post_embeddings: np.ndarray,
        labels: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        combined = np.vstack([pre_embeddings, post_embeddings])
        reduced = self.reduce(combined, labels=None)
        n = len(pre_embeddings)
        for i, point in enumerate(reduced["points"]):
            point["set"] = "pre" if i < n else "post"
        reduced["set"] = "comparison"
        reduced["pre_count"] = n
        reduced["post_count"] = len(post_embeddings)
        return reduced

    def privacy_shift(
        self,
        before_unlearn: np.ndarray,
        after_unlearn: np.ndarray,
        sensitive_indices: Optional[list[int]] = None,
    ) -> dict[str, Any]:
        comparison = self.compare(before_unlearn, after_unlearn)
        shifts = []
        for i in range(len(before_unlearn)):
            shift = float(np.linalg.norm(after_unlearn[i] - before_unlearn[i]))
            shifts.append(shift)
        comparison["privacy_shifts"] = shifts
        comparison["mean_shift"] = float(np.mean(shifts)) if shifts else 0.0
        comparison["max_shift"] = float(np.max(shifts)) if shifts else 0.0
        return comparison
