"""Tests for LangGraph workflow nodes and routing."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.retriever import RetrievedChunk
from app.workflow import nodes
from app.workflow.state import WorkflowState


# —— validate_input ——

def test_validate_input_empty_query():
    state: WorkflowState = {"query": ""}
    result = nodes.validate_input(state)
    assert result["needs_clarification"] is True
    assert "error" in result


def test_validate_input_too_long():
    state: WorkflowState = {"query": "x" * 3000}
    result = nodes.validate_input(state)
    assert result["needs_clarification"] is True


def test_validate_input_valid():
    state: WorkflowState = {"query": "My Wi-Fi is not connecting."}
    result = nodes.validate_input(state)
    assert result.get("needs_clarification") is False
    assert result.get("error") is None


def test_validate_input_strips_whitespace():
    state: WorkflowState = {"query": "  My issue   "}
    result = nodes.validate_input(state)
    assert result["query"] == "My issue"


# —— classify_ticket ——

def test_classify_ticket_returns_classification():
    state: WorkflowState = {"query": "Cannot connect to VPN"}
    result = nodes.classify_ticket(state)
    assert result["classification"] is not None
    assert result["classification"].method == "rules"


# —— assess_evidence ——

def test_assess_evidence_sufficient(sample_chunks):
    state: WorkflowState = {"retrieved_chunks": sample_chunks}
    result = nodes.assess_evidence(state)
    assert result["evidence_sufficient"] is True


def test_assess_evidence_insufficient():
    state: WorkflowState = {"retrieved_chunks": []}
    result = nodes.assess_evidence(state)
    assert result["evidence_sufficient"] is False


# —— generate_answer ——

def test_generate_answer_calls_llm(sample_chunks):
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Step 1: Restart the router."
    state: WorkflowState = {"query": "Wi-Fi broken", "retrieved_chunks": sample_chunks}
    result = nodes.generate_answer(state, llm_provider=mock_llm)
    assert result["answer"] == "Step 1: Restart the router."
    mock_llm.generate.assert_called_once()


def test_generate_answer_handles_llm_failure(sample_chunks):
    mock_llm = MagicMock()
    mock_llm.generate.side_effect = Exception("API timeout")
    state: WorkflowState = {"query": "Wi-Fi broken", "retrieved_chunks": sample_chunks}
    result = nodes.generate_answer(state, llm_provider=mock_llm)
    assert "error" in result
    assert result["answer"]  # Should still return something


# —— handle_insufficient_evidence ——

def test_handle_insufficient_evidence_returns_clarification():
    state: WorkflowState = {"query": "Something vague", "retrieved_chunks": []}
    result = nodes.handle_insufficient_evidence(state)
    assert result["needs_clarification"] is True
    assert "sources" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0
