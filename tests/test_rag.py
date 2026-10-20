"""Tests for RAG components: context builder, generator, embeddings."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.context_builder import build_context, format_sources
from app.rag.embeddings import MockEmbeddingProvider, get_embedding_provider
from app.rag.generator import MockLLMProvider, get_llm_provider
from app.rag.retriever import RetrievedChunk


# —— Context builder tests ——

def test_build_context_empty_chunks():
    assert build_context([]) == ""


def test_build_context_includes_doc_id(sample_chunks):
    context = build_context(sample_chunks)
    assert "KB-NET-001" in context


def test_build_context_includes_text(sample_chunks):
    context = build_context(sample_chunks)
    assert "Device Manager" in context


def test_format_sources_empty():
    assert format_sources([]) == []


def test_format_sources_deduplicates(sample_chunks):
    # Duplicate the first chunk
    doubled = sample_chunks + [sample_chunks[0]]
    sources = format_sources(doubled)
    keys = [f"{s['doc_id']}:{s['chunk_index']}" for s in sources]
    assert len(keys) == len(set(keys))


def test_format_sources_has_excerpt(sample_chunks):
    sources = format_sources(sample_chunks)
    assert all("excerpt" in s for s in sources)


# —— Embedding tests ——

def test_mock_embedding_returns_correct_dimension():
    provider = MockEmbeddingProvider()
    vectors = provider.embed(["test"])
    assert len(vectors) == 1
    assert len(vectors[0]) == MockEmbeddingProvider.DIMENSION


def test_mock_embedding_query_returns_vector():
    provider = MockEmbeddingProvider()
    vec = provider.embed_query("my query")
    assert len(vec) == MockEmbeddingProvider.DIMENSION


def test_get_embedding_provider_mock():
    provider = get_embedding_provider("mock")
    assert isinstance(provider, MockEmbeddingProvider)


def test_get_embedding_provider_invalid():
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedding_provider("unknown_provider")


# —— Generator tests ——

def test_mock_llm_no_context():
    llm = MockLLMProvider()
    response = llm.generate("help", "")
    assert "[MOCK MODE" in response
    assert "knowledge base" in response.lower()


def test_mock_llm_with_context(sample_chunks):
    llm = MockLLMProvider()
    context = build_context(sample_chunks)
    response = llm.generate("Wi-Fi not working", context)
    assert "[MOCK MODE" in response


def test_get_llm_provider_mock():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)


def test_get_llm_provider_openai_without_key():
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        get_llm_provider("openai", api_key="")


def test_get_llm_provider_unknown():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("anthropic")
