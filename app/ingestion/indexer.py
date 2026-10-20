"""Embed document chunks and persist them in a ChromaDB vector store.

The indexer is idempotent: running it twice on the same documents will
not create duplicate entries because chunks are upserted by chunk_id.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.exceptions import IngestionError
from app.core.logging_config import get_logger
from app.ingestion.loader import DocumentChunk

if TYPE_CHECKING:
    from app.rag.embeddings import EmbeddingProvider

logger = get_logger(__name__)

BATCH_SIZE = 64  # Embed and upsert in batches to control memory usage


class VectorIndexer:
    """Manages embedding and storage of document chunks in ChromaDB."""

    def __init__(
        self,
        store_path: Path,
        collection_name: str,
        embedding_provider: "EmbeddingProvider",
    ) -> None:
        self._embedding_provider = embedding_provider
        self._client = chromadb.PersistentClient(
            path=str(store_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store opened: path=%s, collection=%s, existing_docs=%d",
            store_path,
            collection_name,
            self._collection.count(),
        )

    def index(self, chunks: list[DocumentChunk]) -> int:
        """Embed and upsert *chunks* into the collection.

        Returns the number of chunks upserted.
        """
        if not chunks:
            logger.warning("No chunks provided to index.")
            return 0

        total_upserted = 0
        for batch_start in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[batch_start : batch_start + BATCH_SIZE]
            texts = [c.text for c in batch]

            try:
                embeddings = self._embedding_provider.embed(texts)
            except Exception as exc:
                raise IngestionError(f"Embedding failed for batch: {exc}") from exc

            self._collection.upsert(
                ids=[c.chunk_id for c in batch],
                embeddings=embeddings,
                documents=[c.text for c in batch],
                metadatas=[
                    {
                        "source": c.source,
                        "doc_id": c.doc_id,
                        "chunk_index": c.chunk_index,
                    }
                    for c in batch
                ],
            )
            total_upserted += len(batch)
            logger.debug("Upserted batch of %d chunks", len(batch))

        # This collection is a snapshot of the supplied document directory.
        # Remove stale chunks only after every new batch has been written successfully.
        current_ids = {c.chunk_id for c in chunks}
        existing_ids = self._collection.get(include=[])['ids']
        stale_ids = [item for item in existing_ids if item not in current_ids]
        for start in range(0, len(stale_ids), BATCH_SIZE):
            self._collection.delete(ids=stale_ids[start:start + BATCH_SIZE])
        logger.info("Indexed %d chunks into vector store.", total_upserted)
        return total_upserted

    def count(self) -> int:
        """Return the number of chunks currently in the collection."""
        return self._collection.count()

    def reset(self) -> None:
        """Delete all documents in the collection (allows a clean rebuild)."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Vector store collection reset.")
