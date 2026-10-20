"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import os
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"

import pytest

from app.rag.embeddings import MockEmbeddingProvider
from app.rag.retriever import RetrievedChunk


@pytest.fixture
def mock_embedding_provider():
    """Deterministic mock embedding provider for tests."""
    return MockEmbeddingProvider()


@pytest.fixture
def sample_chunks():
    """A small set of pre-built document chunks for retrieval tests."""
    return [
        RetrievedChunk(
            text="Check Device Manager for yellow warning icons on the Wi-Fi adapter.",
            source="wifi_troubleshooting.md",
            doc_id="KB-NET-001",
            chunk_index=0,
            score=0.85,
        ),
        RetrievedChunk(
            text="Corporate accounts are locked after 5 consecutive failed login attempts.",
            source="password_reset.md",
            doc_id="KB-AUTH-001",
            chunk_index=1,
            score=0.78,
        ),
    ]


@pytest.fixture
def sample_docs_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with two sample documents."""
    docs = tmp_path / "sample_docs"
    docs.mkdir()
    (docs / "wifi.md").write_text(
        "# Wi-Fi Guide\n**Document ID:** KB-NET-001\nRestart the router to fix Wi-Fi issues.",
        encoding="utf-8",
    )
    (docs / "password.md").write_text(
        "# Password Guide\n**Document ID:** KB-AUTH-001\nReset your password via the SSPR portal.",
        encoding="utf-8",
    )
    return docs
