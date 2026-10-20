"""LangGraph workflow graph for the IT support agent.

Builds and compiles a StateGraph with conditional routing:

  validate_input
      │ (if error) → END
      ↓
  classify_ticket
      ↓
  retrieve_evidence
      ↓
  assess_evidence
      ├ (insufficient) → handle_insufficient_evidence → END
      └ (sufficient)   → generate_answer → END
"""

from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from app.core.logging_config import get_logger
from app.rag.generator import LLMProvider
from app.rag.retriever import Retriever
from app.workflow import nodes
from app.workflow.state import WorkflowState

logger = get_logger(__name__)


def _route_after_validation(state: WorkflowState) -> str:
    """Route to END if validation failed, otherwise continue."""
    if state.get("needs_clarification") or state.get("error"):
        return "end_with_error"
    return "classify_ticket"


def _route_after_evidence(state: WorkflowState) -> str:
    """Route based on whether sufficient evidence was retrieved."""
    if state.get("evidence_sufficient"):
        return "generate_answer"
    return "handle_insufficient_evidence"


def build_graph(retriever: Retriever, llm_provider: LLMProvider) -> Any:
    """Construct and compile the LangGraph support-agent graph.

    Args:
        retriever: Configured :class:`Retriever` instance.
        llm_provider: Configured :class:`LLMProvider` instance.

    Returns:
        A compiled LangGraph runnable.
    """
    graph = StateGraph(WorkflowState)

    # —— Register nodes ——
    graph.add_node("validate_input", nodes.validate_input)
    graph.add_node("classify_ticket", nodes.classify_ticket)
    graph.add_node(
        "retrieve_evidence",
        partial(nodes.retrieve_evidence, retriever=retriever),
    )
    graph.add_node("assess_evidence", nodes.assess_evidence)
    graph.add_node(
        "generate_answer",
        partial(nodes.generate_answer, llm_provider=llm_provider),
    )
    graph.add_node("handle_insufficient_evidence", nodes.handle_insufficient_evidence)

    # —— Entry point ——
    graph.set_entry_point("validate_input")

    # —— Edges ——
    graph.add_conditional_edges(
        "validate_input",
        _route_after_validation,
        {"end_with_error": END, "classify_ticket": "classify_ticket"},
    )
    graph.add_edge("classify_ticket", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "assess_evidence")
    graph.add_conditional_edges(
        "assess_evidence",
        _route_after_evidence,
        {
            "generate_answer": "generate_answer",
            "handle_insufficient_evidence": "handle_insufficient_evidence",
        },
    )
    graph.add_edge("generate_answer", END)
    graph.add_edge("handle_insufficient_evidence", END)

    compiled = graph.compile()
    logger.info("LangGraph support-agent workflow compiled.")
    return compiled
