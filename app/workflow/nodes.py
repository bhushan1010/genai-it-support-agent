"""LangGraph node functions for the IT support workflow.

Each node is a pure function that takes the current WorkflowState
and returns a dict of state updates. Nodes do not mutate state directly.

Nodes:
  1. validate_input    — reject empty or oversized queries
  2. classify_ticket   — categorise the support request
  3. retrieve_evidence — fetch relevant KB chunks
  4. assess_evidence   — decide if evidence is sufficient
  5. generate_answer   — produce a grounded response
  6. handle_insufficient_evidence — ask for clarification or recommend escalation
"""

from __future__ import annotations

from typing import Any

from app.core.logging_config import get_logger
from app.core.config import settings
from app.rag.context_builder import build_context, format_sources, select_context_chunks
from app.services.classifier import classify
from app.workflow.state import WorkflowState

logger = get_logger(__name__)

MAX_QUERY_LENGTH = 2000  # characters
MIN_EVIDENCE_CHUNKS = 1  # require at least this many chunks above threshold


def validate_input(state: WorkflowState) -> dict:
    """Validate the user query and reject clearly malformed input."""
    query: str = state.get("query", "").strip()

    if not query:
        return {
            "error": "Query is empty. Please describe your IT issue.",
            "needs_clarification": True,
        }

    if len(query) > MAX_QUERY_LENGTH:
        return {
            "error": (
                f"Query exceeds the maximum length of {MAX_QUERY_LENGTH} characters. "
                "Please shorten your description."
            ),
            "needs_clarification": True,
        }

    # Normalise whitespace in state
    return {"query": query, "error": None, "needs_clarification": False}


def contextual_query(state: WorkflowState) -> str:
    """Use the last two user turns to resolve short, ambiguous follow-ups."""
    query = state.get("query", "")
    from app.services.classifier import TicketCategory
    if state.get("issue_query"):
        return state["issue_query"] if state["issue_query"] == query else state["issue_query"] + "\n" + query
    if classify(query).category != TicketCategory.UNKNOWN:
        return query
    previous = [m["content"] for m in state.get("conversation_history", []) if m["role"] == "user"][-2:]
    return "\n".join([*previous, query])


def classify_ticket(state: WorkflowState) -> dict:
    """Classify the query into an IT support category."""
    query = state.get("query", "")
    result = classify(contextual_query(state))
    logger.info(
        "Classification: %s (confidence=%s)", result.category.value, result.confidence
    )
    return {"classification": result}


def retrieve_evidence(state: WorkflowState, retriever: Any) -> dict:
    """Retrieve relevant chunks from the knowledge base.

    Args:
        state: Current workflow state.
        retriever: A :class:`app.rag.retriever.Retriever` instance.
            Passed via partial application when building the graph.
    """
    query = state.get("query", "")
    try:
        chunks = retriever.retrieve(contextual_query(state))
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return {
            "retrieved_chunks": [],
            "error": f"Retrieval failed: {exc}",
        }
    return {"retrieved_chunks": chunks}


def assess_evidence(state: WorkflowState) -> dict:
    """Determine whether the retrieved evidence is sufficient to answer."""
    chunks = state.get("retrieved_chunks", [])
    chunks = [c for c in chunks if c.score >= settings.retrieval_score_threshold]
    sufficient = not state.get("error") and len(chunks) >= MIN_EVIDENCE_CHUNKS
    logger.info(
        "Evidence assessment: %d chunk(s) retrieved, sufficient=%s",
        len(chunks),
        sufficient,
    )
    return {"evidence_sufficient": bool(sufficient), "retrieved_chunks": chunks}


def generate_answer(state: WorkflowState, llm_provider: Any) -> dict:
    """Generate a grounded answer using the retrieved evidence.

    Args:
        state: Current workflow state.
        llm_provider: A :class:`app.rag.generator.LLMProvider` instance.
    """
    query = state.get("query", "")
    chunks = state.get("retrieved_chunks", [])
    from app.rag.generator import ExtractiveProvider
    if isinstance(llm_provider, ExtractiveProvider):
        from app.rag.local_support import extract_guidance
        result = extract_guidance(chunks, state.get("attempts", []), llm_provider.sections)
        result["sources"] = format_sources(result["sources"])
        return result
    chunks = select_context_chunks(chunks)
    context = build_context(chunks)
    sources = format_sources(chunks)

    try:
        answer = llm_provider.generate(query, context, history=state.get("conversation_history", []))
        if not answer.strip():
            raise ValueError("Empty model response")
    except Exception as exc:
        logger.error("Generation failed: %s", exc)
        return {
            "answer": "Answer generation failed. Please try again or contact the helpdesk.",
            "sources": sources,
            "error": str(exc),
        }

    return {"answer": answer, "sources": sources}


def handle_insufficient_evidence(state: WorkflowState) -> dict:
    """Return a clarification or escalation message when evidence is lacking."""
    classification = state.get("classification")
    category_label = (
        classification.label if classification else "your IT issue"
    )

    answer = (
        f"I was unable to find sufficient information in the knowledge base to address "
        f"your question about {category_label}.\n\n"
        f"To help you better, please provide:\n"
        f"- The exact error message you are seeing (if any)\n"
        f"- The name and version of the affected application or system\n"
        f"- The operating system and version\n"
        f"- When the issue started\n\n"
        f"If the issue is urgent, please contact the IT helpdesk directly."
    )
    return {
        "answer": answer,
        "sources": [],
        "needs_clarification": True,
        "needs_escalation": False,
    }
