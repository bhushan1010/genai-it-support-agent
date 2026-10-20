"""LangGraph workflow state definition.

The WorkflowState TypedDict carries all data through the graph.
Using TypedDict gives type hints while remaining compatible with
LangGraph's state management.
"""

from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from app.rag.retriever import RetrievedChunk
from app.services.classifier import ClassificationResult


class WorkflowState(TypedDict, total=False):
    """Mutable state that flows through the LangGraph support-agent graph."""

    # Input
    issue_query: Optional[str]
    attempts: list[dict[str, str]]
    steps: list[dict[str, str]]
    resolved: bool
    query: str
    conversation_history: list[dict[str, str]]

    # After classification
    classification: Optional[ClassificationResult]

    # After retrieval
    retrieved_chunks: list[RetrievedChunk]
    evidence_sufficient: bool

    # After generation
    answer: str
    sources: list[dict[str, Any]]

    # Control
    needs_clarification: bool
    needs_escalation: bool
    error: Optional[str]
