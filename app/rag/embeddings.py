"""Embedding provider abstraction.

Provides a single interface for generating text embeddings whether using
a local sentence-transformers model (no API key) or an OpenAI embedding
model (requires API key).

For offline testing and local demos, use the 'local' provider with the
default model 'all-MiniLM-L6-v2'.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for all embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors for the given texts."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Return the embedding vector for a single query string."""


class LocalEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using a local sentence-transformers model.

    No API key required. The model is downloaded on first use and cached
    in the sentence-transformers cache directory (~/.cache/torch/sentence_transformers).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        # Lazy import so the module loads even if sentence-transformers is absent
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for the local embedding provider. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        logger.info("Loading local embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        logger.info("Local embedding model loaded.")

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode([text], show_progress_bar=False, normalize_embeddings=True)
        return vector[0].tolist()


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic zero-vector embeddings for unit tests.

    NOT suitable for real retrieval — all vectors are identical.
    Use only in tests to avoid loading a real model.
    """

    DIMENSION = 384  # Match all-MiniLM-L6-v2 dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self.DIMENSION for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * self.DIMENSION


def get_embedding_provider(
    provider: str = "local", model_name: str = "all-MiniLM-L6-v2"
) -> EmbeddingProvider:
    """Return the appropriate embedding provider for the given configuration."""
    if provider == "local":
        return LocalEmbeddingProvider(model_name)
    if provider == "mock":
        return MockEmbeddingProvider()
    raise ValueError(
        f"Unknown embedding provider: '{provider}'. Supported: 'local', 'mock'."
    )
