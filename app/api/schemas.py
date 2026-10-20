"""Pydantic request and response models for the support API.

All user-facing models are validated by FastAPI before reaching the
business logic. Keep schemas separate from domain models.
"""

from __future__ import annotations

from typing import Any, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class AttemptOutcome(BaseModel):
    step_id: str = Field(pattern=r"^[a-f0-9]{20}$")
    outcome: Literal["tried", "worked", "did_not_work"]


class ProcedurePrerequisite(BaseModel):
    text: str
    doc_id: str
    source_section: str
    source_quote: str = ""


class TroubleshootingStep(BaseModel):
    sequence: list[str] = Field(default_factory=list)
    position: Optional[int] = None
    prerequisites: list[ProcedurePrerequisite] = Field(default_factory=list)
    step_id: str
    title: str
    text: str
    doc_id: str


class UploadedRulebook(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[^/\\]+\.(?:md|txt)$")
    content: str = Field(min_length=1, max_length=100_000)

    @field_validator("content")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Rulebook cannot be empty")
        if len(value.encode("utf-8")) > 100_000:
            raise ValueError("Each rulebook must not exceed 100 KB")
        return value


class SupportRequest(BaseModel):
    """Incoming request for IT support assistance."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="The IT support question or issue description.",
        examples=["My laptop cannot connect to Wi-Fi after a Windows update."],
    )
    rulebooks: list[UploadedRulebook] = Field(default_factory=list, max_length=3)
    internet_fallback: bool = False
    attempts: list[AttemptOutcome] = Field(default_factory=list, max_length=100)
    issue_query: Optional[str] = Field(default=None, min_length=3, max_length=2000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=10)
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for tracking a multi-turn conversation.",
    )

    @model_validator(mode="after")
    def upload_budget(self):
        if sum(len(book.content.encode("utf-8")) for book in self.rulebooks) > 200_000:
            raise ValueError("Combined rulebooks must not exceed 200 KB")
        return self

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Query must contain at least 3 non-whitespace characters")
        return v


class SourceReference(BaseModel):
    """A reference to a knowledge-base document used in the answer."""

    doc_id: str
    source: str
    chunk_index: int
    url: Optional[str] = None
    fetched_at: Optional[str] = None
    relevance_score: float
    excerpt: str


class SupportResponse(BaseModel):
    """Response from the support agent."""

    knowledge_origin: str = "sample_runbook"
    analysis: list[str] = Field(default_factory=list)
    steps: list[TroubleshootingStep] = Field(default_factory=list)
    resolved: bool = False
    needs_escalation: bool = False
    answer_mode: str = "mock"
    answer: str = Field(description="The generated troubleshooting guidance.")
    category: str = Field(description="Classified ticket category label.")
    category_id: str = Field(description="Machine-readable category identifier.")
    evidence_sufficient: bool = Field(
        description="Whether sufficient knowledge-base evidence was found."
    )
    sources: list[SourceReference] = Field(
        default_factory=list,
        description="Knowledge-base sources cited in the answer.",
    )
    needs_clarification: bool = Field(default=False)
    mock_mode: bool = Field(
        description="True when a mock LLM is in use. No real AI model was queried."
    )
    disclaimer: str = Field(
        default=(
            "This is AI-generated troubleshooting guidance. "
            "Review all steps before applying them. "
            "Contact the IT helpdesk for urgent or complex issues."
        )
    )


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    vector_store_docs: int
    llm_provider: str
    mock_mode: bool
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str
    detail: Optional[str] = None
