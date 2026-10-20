"""CLI script to ingest documents into the vector store.

Usage:
    python scripts/ingest.py [--reset]

Options:
    --reset     Delete existing vector store and rebuild from scratch.
                Without this flag, new documents are upserted (no duplicates).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.ingestion.indexer import VectorIndexer
from app.ingestion.loader import load_documents
from app.rag.embeddings import get_embedding_provider

configure_logging(settings.log_level)
logger = get_logger("ingest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest IT support documents.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild the vector store from scratch.",
    )
    parser.add_argument(
        "--docs-path",
        type=Path,
        default=settings.docs_path,
        help=f"Path to documents directory (default: {settings.docs_path}).",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("IT Support Agent — Document Ingestion")
    logger.info("=" * 60)
    logger.info("Documents path: %s", args.docs_path)
    logger.info("Vector store:   %s", settings.vector_store_path)
    logger.info("Collection:     %s", settings.vector_store_collection)
    logger.info("Embedding:      %s / %s", settings.embedding_provider, settings.embedding_model)
    logger.info("Chunk size:     %d words (overlap: %d)", settings.chunk_size, settings.chunk_overlap)

    # Load documents
    logger.info("Loading documents...")
    try:
        chunks = load_documents(
            args.docs_path,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
    except Exception as exc:
        logger.error("Failed to load documents: %s", exc)
        sys.exit(1)

    logger.info("Loaded %d chunk(s) from documents.", len(chunks))

    # Initialise embedding provider
    logger.info("Initialising embedding provider...")
    try:
        embedding_provider = get_embedding_provider(
            settings.embedding_provider, settings.embedding_model
        )
    except Exception as exc:
        logger.error("Embedding provider failed: %s", exc)
        sys.exit(1)

    # Index
    settings.vector_store_path.mkdir(parents=True, exist_ok=True)
    indexer = VectorIndexer(
        store_path=settings.vector_store_path,
        collection_name=settings.vector_store_collection,
        embedding_provider=embedding_provider,
    )

    if args.reset:
        logger.info("--reset flag set: clearing existing vector store.")
        indexer.reset()

    logger.info("Embedding and indexing chunks...")
    try:
        count = indexer.index(chunks)
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("[OK] Ingestion complete: %d chunk(s) indexed.", count)
    logger.info("Total documents in store: %d", indexer.count())
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
