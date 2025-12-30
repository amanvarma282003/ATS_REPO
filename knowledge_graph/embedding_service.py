from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Iterable, List

import numpy as np
from django.conf import settings
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Singleton wrapper around the Qwen3 embedding model."""

    def __init__(self):
        cache_dir = Path(settings.EMBEDDING_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.query_prompt_name = getattr(settings, "EMBEDDING_QUERY_PROMPT", None)
        self.model = SentenceTransformer(
            self.model_name,
            cache_folder=str(cache_dir),
        )

    def encode(self, texts: Iterable[str], *, as_query: bool = False) -> List[np.ndarray]:
        """Encode texts into normalized embeddings.

        Args:
            texts: Iterable of input strings.
            as_query: Whether to apply the model's query prompt/instructions.
        Returns:
            List of numpy arrays (float32) with unit length.
        """
        texts = [text for text in texts if text is not None]
        if not texts:
            return []

        encode_kwargs = {"normalize_embeddings": True}
        if as_query and self.query_prompt_name:
            encode_kwargs["prompt_name"] = self.query_prompt_name

        embeddings = self.model.encode(texts, **encode_kwargs)
        if isinstance(embeddings, np.ndarray):
            return [embeddings[i] for i in range(len(texts))]
        return embeddings


_service: EmbeddingService | None = None
_service_lock = Lock()


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = EmbeddingService()
    return _service
