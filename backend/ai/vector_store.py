from __future__ import annotations

from datetime import datetime, timedelta, timezone

import faiss
import numpy as np

from backend.utils.models import ContextDocument


class FaissVectorStore:
    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.documents: list[ContextDocument] = []
        self.dimension: int | None = None
        self.last_built_at: datetime | None = None

    def rebuild(self, documents: list[ContextDocument], vectors: np.ndarray) -> None:
        self.documents = documents
        if vectors.size == 0:
            self.index = None
            self.dimension = None
            self.last_built_at = datetime.now(timezone.utc)
            return

        self.dimension = int(vectors.shape[1])
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(vectors)
        self.last_built_at = datetime.now(timezone.utc)

    def needs_refresh(self, refresh_minutes: int) -> bool:
        if self.index is None or self.last_built_at is None:
            return True
        return datetime.now(timezone.utc) - self.last_built_at >= timedelta(minutes=refresh_minutes)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[ContextDocument, float]]:
        if self.index is None or not self.documents:
            return []

        vector = np.asarray([query_vector], dtype="float32")
        scores, indices = self.index.search(vector, min(top_k, len(self.documents)))
        matches: list[tuple[ContextDocument, float]] = []

        for index, score in zip(indices[0], scores[0], strict=False):
            if index == -1:
                continue
            matches.append((self.documents[index], float(score)))
        return matches

