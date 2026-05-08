from __future__ import annotations

from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.utils.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        vector = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vector.astype("float32")

    def embed_batch(self, texts: Iterable[str]) -> np.ndarray:
        vectors = self.model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.astype("float32")

