"""Tests for document loading and chunking."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import IngestionError
from app.ingestion.loader import (
    DocumentChunk,
    _clean_text,
    _extract_doc_id,
    _split_into_chunks,
    load_documents,
)


def test_split_into_chunks_basic():
    words = "word " * 600  # 600 words
    chunks = _split_into_chunks(words.strip(), chunk_size=512, overlap=64)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_split_single_short_document():
    text = "This is a short document."
    chunks = _split_into_chunks(text, chunk_size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_clean_text_removes_excessive_blank_lines():
    text = "line1\n\n\n\n\nline2"
    cleaned = _clean_text(text)
    assert "\n\n\n" not in cleaned


def test_extract_doc_id_from_header():
    content = "**Document ID:** KB-NET-001\nSome content."
    assert _extract_doc_id(content, "wifi.md") == "KB-NET-001"


def test_extract_doc_id_fallback_to_filename():
    content = "No header here."
    assert _extract_doc_id(content, "wifi_troubleshooting.md") == "WIFI-TROUBLESHOOTING"


def test_load_documents_missing_directory():
    with pytest.raises(IngestionError, match="not found"):
        load_documents(Path("/nonexistent/path"))


def test_load_documents_empty_directory(tmp_path):
    with pytest.raises(IngestionError, match="No supported"):
        load_documents(tmp_path)


def test_load_documents_success(sample_docs_dir):
    chunks = load_documents(sample_docs_dir, chunk_size=50, chunk_overlap=5)
    assert len(chunks) >= 2
    assert all(isinstance(c, DocumentChunk) for c in chunks)
    assert all(c.doc_id for c in chunks)
    assert all(c.source for c in chunks)
    assert all(c.chunk_id for c in chunks)


def test_chunk_id_is_unique(sample_docs_dir):
    chunks = load_documents(sample_docs_dir)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"


def test_load_documents_skips_unsupported_files(tmp_path):
    (tmp_path / "guide.md").write_text(
        "# Doc\n**Document ID:** KB-TEST-001\nContent here.", encoding="utf-8"
    )
    (tmp_path / "image.png").write_bytes(b"\x89PNG")
    chunks = load_documents(tmp_path)
    assert len(chunks) >= 1
