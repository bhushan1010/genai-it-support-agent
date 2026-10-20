"""Load, validate, and chunk text documents from a directory.

Supported formats: .txt, .md
All loaded chunks carry source metadata so retrieval results can be traced back
to their origin document.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from app.core.exceptions import IngestionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".md", ".txt"}
MAX_FILE_SIZE_BYTES = 1_000_000  # 1 MB per document


@dataclass
class DocumentChunk:
    """A single chunk of text with its origin metadata."""

    text: str
    source: str              # Filename (basename)
    doc_id: str              # Derived from the document ID header or filename
    chunk_index: int
    chunk_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.chunk_id = hashlib.md5(
            f"{self.doc_id}:{self.chunk_index}:{self.text[:64]}".encode()
        ).hexdigest()[:16]


def _extract_doc_id(content: str, filename: str) -> str:
    """Extract the Document ID from the file header, or derive one from the filename."""
    # Look for a line like: **Document ID:** KB-NET-001
    match = re.search(r"\*{0,2}Document ID:\*{0,2}\s*([\w-]+)", content)
    if match:
        return match.group(1)
    # Fallback: use filename stem
    return Path(filename).stem.upper().replace("_", "-")


def _clean_text(text: str) -> str:
    """Light text normalisation that preserves technical details.

    Removes excessive whitespace while keeping code blocks and
    command syntax intact.
    """
    # Collapse runs of 3+ blank lines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing spaces from lines
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def _split_into_chunks(
    text: str, chunk_size: int = 512, overlap: int = 64
) -> list[str]:
    """Split text into overlapping word-based chunks.

    Word-boundary splitting avoids cutting commands or technical terms
    in the middle of a token.
    """
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def load_documents(
    docs_path: Path,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[DocumentChunk]:
    """Read all supported documents from *docs_path* and return chunked results.

    Args:
        docs_path: Directory containing IT support documents.
        chunk_size: Target chunk size in words.
        chunk_overlap: Number of overlapping words between successive chunks.

    Returns:
        A list of :class:`DocumentChunk` objects ready for embedding.

    Raises:
        IngestionError: If the directory does not exist or no files can be read.
    """
    if not docs_path.exists() or not docs_path.is_dir():
        raise IngestionError(
            f"Documents directory not found: {docs_path}. "
            "Create the directory and add your IT support documents."
        )

    chunks: list[DocumentChunk] = []
    files_processed = 0
    files_failed = 0

    for file_path in sorted(docs_path.iterdir()):
        if not file_path.is_file() or file_path.name.lower() == "readme.md":
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug("Skipping unsupported file: %s", file_path.name)
            continue
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            logger.warning(
                "Skipping oversized file (%s bytes): %s",
                file_path.stat().st_size,
                file_path.name,
            )
            files_failed += 1
            continue

        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.error("Cannot read %s: %s", file_path.name, exc)
            files_failed += 1
            continue

        if not raw.strip():
            logger.warning("Skipping empty file: %s", file_path.name)
            continue

        cleaned = _clean_text(raw)
        doc_id = _extract_doc_id(raw, file_path.name)
        raw_chunks = _split_into_chunks(cleaned, chunk_size, chunk_overlap)

        for idx, text in enumerate(raw_chunks):
            chunks.append(
                DocumentChunk(
                    text=text,
                    source=file_path.name,
                    doc_id=doc_id,
                    chunk_index=idx,
                )
            )

        files_processed += 1
        logger.info(
            "Loaded %s: doc_id=%s, %d chunks", file_path.name, doc_id, len(raw_chunks)
        )

    if files_processed == 0:
        raise IngestionError(
            f"No supported documents ({SUPPORTED_EXTENSIONS}) found in {docs_path}."
        )

    logger.info(
        "Ingestion complete: %d file(s) loaded, %d chunk(s) total, %d file(s) failed",
        files_processed,
        len(chunks),
        files_failed,
    )
    return chunks
