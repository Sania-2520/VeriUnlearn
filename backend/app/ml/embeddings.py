from __future__ import annotations


from loguru import logger
from sentence_transformers import SentenceTransformer



class EmbeddingEngine:
    _instance: EmbeddingEngine | None = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> EmbeddingEngine:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.model_name = "all-MiniLM-L6-v2"
        self._load_error: str | None = None
        logger.info(f"EmbeddingEngine initialized (model={self.model_name})")

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Embedding model loaded: {self.model_name}")
            return True
        except Exception as e:
            self._load_error = str(e)
            logger.error(f"Failed to load embedding model: {e}")
            return False

    def embed(self, text: str) -> list[float]:
        if not self._ensure_model():
            return [0.0] * 384
        result = self._model.encode(text, normalize_embeddings=True)
        return result.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._ensure_model():
            return [[0.0] * 384 for _ in texts]
        results = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [r.tolist() for r in results]

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return 384
