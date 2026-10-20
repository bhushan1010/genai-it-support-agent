"""FastAPI route handlers for the IT support agent API.

Business logic is delegated to the workflow graph, keeping handlers thin
and independently testable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.schemas import (
    ErrorResponse,
    HealthResponse,
    SourceReference,
    SupportRequest,
    SupportResponse,
)
from app.core.exceptions import InsufficientEvidenceError, RetrievalError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _get_app_state(request: Request) -> dict:
    """Extract application state from the FastAPI app instance."""
    return request.app.state


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service status and vector-store document count.",
)
def health_check(request: Request) -> HealthResponse:
    app_state = _get_app_state(request)
    retriever = getattr(app_state, "retriever", None)
    settings = getattr(app_state, "settings", None)

    doc_count = 0
    if retriever is not None:
        try:
            doc_count = retriever.count() if hasattr(type(retriever), "count") else retriever._collection.count()
        except Exception:
            doc_count = -1

    llm_provider = getattr(settings, "llm_provider", "unknown") if settings else "unknown"

    return HealthResponse(
        status="ok" if retriever is not None and getattr(app_state, "graph", None) is not None and doc_count > 0 else "degraded",
        vector_store_docs=doc_count,
        llm_provider=llm_provider,
        mock_mode=(llm_provider == "mock"),
    )


@router.post(
    "/support",
    response_model=SupportResponse,
    summary="IT support query",
    description=(
        "Submit an IT support question. The agent retrieves relevant knowledge-base "
        "evidence and generates a grounded troubleshooting response."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
def support_query(body: SupportRequest, request: Request) -> SupportResponse:
    app_state = _get_app_state(request)
    graph = getattr(app_state, "graph", None)
    settings = getattr(app_state, "settings", None)

    if graph is None and not body.rulebooks and not body.internet_fallback:
        raise HTTPException(
            status_code=503,
            detail="The support agent is not available. The knowledge base may not be indexed yet.",
        )

    logger.info("Support query received: %.80s", body.query)

    try:
        workflow_state = {
            "query": body.query,
            "issue_query": body.issue_query,
            "attempts": [a.model_dump() for a in body.attempts],
            "conversation_history": [m.model_dump() for m in body.conversation_history],
        }
        if body.rulebooks or body.internet_fallback:
            from app.services.knowledge import resolve_knowledge
            result = resolve_knowledge(body, app_state, workflow_state)
        else:
            result = graph.invoke(workflow_state)
    except Exception as exc:
        logger.error("Workflow error: %s", exc)
        raise HTTPException(status_code=503, detail="The support workflow failed. Please retry or contact the helpdesk.")

    classification = result.get("classification")
    sources_raw = result.get("sources", [])
    sources = [SourceReference(**s) for s in sources_raw]

    llm_provider = getattr(settings, "llm_provider", "mock") if settings else "mock"

    if body.rulebooks or result.get("knowledge_origin") == "internet":
        llm_provider = "extractive"

    return SupportResponse(
        knowledge_origin=result.get("knowledge_origin", "sample_runbook"),
        analysis=result.get("analysis", []),
        disclaimer=("Runbook excerpts. Review prerequisites and applicability before applying. Reported outcomes are not independently verified." if llm_provider == "extractive" else "AI-generated guidance. Review before applying and contact the helpdesk for urgent issues."),
        steps=result.get("steps", []),
        resolved=result.get("resolved", False),
        needs_escalation=result.get("needs_escalation", False),
        answer_mode=llm_provider,
        answer=result.get("answer", "No answer was generated."),
        category=classification.label if classification else "General IT Support",
        category_id=classification.category.value if classification else "general_it",
        evidence_sufficient=result.get("evidence_sufficient", False),
        sources=sources,
        needs_clarification=result.get("needs_clarification", False),
        mock_mode=(llm_provider == "mock"),
    )
