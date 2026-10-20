"""Semantic retrieval from the ChromaDB vector store.

The retriever converts a user query into an embedding and queries the
vector store for the most similar document chunks. It applies a
configurable relevance threshold and returns structured results with
full source metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.exceptions import RetrievalError
from app.core.logging_config import get_logger
from app.rag.embeddings import EmbeddingProvider

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A document chunk returned by the retriever, with metadata."""

    text: str
    source: str      # Filename
    doc_id: str      # Document identifier (e.g. KB-NET-001)
    chunk_index: int
    score: float     # Normalized cosine similarity: (1 + cosine) / 2
    url: str | None = None
    fetched_at: str | None = None


class Retriever:
    """Queries the vector store for chunks relevant to a user question."""

    def __init__(
        self,
        store_path: Path,
        collection_name: str,
        embedding_provider: EmbeddingProvider,
        top_k: int = 5,
        score_threshold: float = 0.6,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._top_k = top_k
        self._score_threshold = score_threshold

        try:
            client = chromadb.PersistentClient(
                path=str(store_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = client.get_collection(collection_name)
        except Exception as exc:
            raise RetrievalError(
                f"Could not open vector store at '{store_path}' "
                f"(collection='{collection_name}'). "
                "Run the ingestion script first: python scripts/ingest.py"
            ) from exc

        logger.info(
            "Retriever ready: collection=%s, docs=%d, top_k=%d, threshold=%.2f",
            collection_name,
            self._collection.count(),
            top_k,
            score_threshold,
        )

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        """Return the top-k chunks most relevant to *query*.

        Chunks with cosine similarity below *score_threshold* are excluded.
        Returns an empty list if the collection is empty or the query is unintelligible.

        Args:
            query: The user's IT support question.

        Returns:
            A list of :class:`RetrievedChunk` sorted by descending relevance.

        Raises:
            RetrievalError: If the vector-store query fails unexpectedly.
        """
        if not query.strip():
            logger.warning("Empty query submitted to retriever.")
            return []

        try:
            if self._collection.count() == 0:
                return []
            query_embedding = self._embedding_provider.embed_query(query)
        except Exception as exc:
            raise RetrievalError(f"Query embedding failed: {exc}") from exc

        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(self._top_k, self._collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise RetrievalError(f"Vector store query failed: {exc}") from exc

        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for text, meta, dist in zip(docs, metas, distances):
            # ChromaDB returns cosine distance (0=identical, 2=opposite).
            # Convert to similarity: 1 - dist/2  (range 0–1).
            similarity = max(0.0, 1.0 - dist / 2.0)
            if similarity < self._score_threshold:
                logger.debug(
                    "Chunk below threshold (%.3f < %.3f): %s",
                    similarity,
                    self._score_threshold,
                    meta.get("doc_id", "?"),
                )
                continue
            chunks.append(
                RetrievedChunk(
                    text=text,
                    source=meta.get("source", "unknown"),
                    doc_id=meta.get("doc_id", "unknown"),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    score=round(similarity, 4),
                )
            )

        chunks.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            "Retrieved %d chunk(s) for query (%.60s...)", len(chunks), query
        )
        return chunks
