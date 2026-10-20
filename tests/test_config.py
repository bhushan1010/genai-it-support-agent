"""Tests for application configuration."""

from __future__ import annotations

import pytest
from app.core.config import Settings


def test_default_settings_use_mock_provider():
    s = Settings()
    assert s.llm_provider == "mock"  # conftest explicitly sets test provider


def test_mock_provider_does_not_require_api_key():
    s = Settings(llm_provider="mock")
    # Should not raise
    s.validate_llm_config()


def test_openai_provider_requires_api_key():
    s = Settings(llm_provider="openai", llm_api_key="")
    with pytest.raises(ValueError, match="LLM_API_KEY is required"):
        s.validate_llm_config()


def test_openai_provider_with_key_does_not_raise():
    s = Settings(llm_provider="openai", llm_api_key="sk-test-key")
    s.validate_llm_config()  # Should not raise


def test_chunk_size_validation():
    with pytest.raises(Exception):
        Settings(chunk_size=10)  # Below minimum of 64


def test_retrieval_top_k_bounds():
    s = Settings(retrieval_top_k=3)
    assert s.retrieval_top_k == 3
