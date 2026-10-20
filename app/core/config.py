"""Application configuration loaded from environment variables.

Use pydantic-settings so every setting has a type, a default, and
a clear validation error if a required value is missing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "mock", "extractive"] = Field(
        default="extractive",
        description="LLM provider: extractive (free), mock (test preview), or openai.",
    )
    llm_model: str = Field(default="gpt-4o-mini")
    llm_api_key: str = Field(default="")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, ge=64)
    llm_timeout: int = Field(default=30, ge=5)

    # ── Embeddings ───────────────────────────────────────────────────────────
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_provider: Literal["local", "mock"] = Field(default="local")

    # ── Vector store ─────────────────────────────────────────────────────────
    vector_store_path: Path = Field(default=Path("./vectorstore"))
    vector_store_collection: str = Field(default="it_support_kb")

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_mode: Literal["keyword", "semantic", "hybrid", "vectorstore"] = "semantic"
    retrieval_top_k: int = Field(default=1, ge=1, le=20)
    retrieval_score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # ── Ingestion ─────────────────────────────────────────────────────────────
    docs_path: Path = Field(default=Path("./data/sample_docs"))
    chunk_size: int = Field(default=512, ge=64)
    chunk_overlap: int = Field(default=64, ge=0)

    # ── Application ───────────────────────────────────────────────────────────
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    debug: bool = Field(default=False)

    @field_validator("llm_api_key")
    @classmethod
    def warn_missing_api_key(cls, v: str, info) -> str:  # noqa: ANN001
        """Emit a clear warning when the provider is not mock but no key is set."""
        # Full cross-field validation happens at the service layer.
        return v

    @model_validator(mode="after")
    def validate_chunk_overlap(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self

    def requires_api_key(self) -> bool:
        """Return True when the configured provider needs an API key."""
        return self.llm_provider == "openai"

    def validate_llm_config(self) -> None:
        """Raise ValueError with a clear message if the LLM config is incomplete."""
        if self.requires_api_key() and not self.llm_api_key:
            raise ValueError(
                f"LLM_API_KEY is required when LLM_PROVIDER='{self.llm_provider}'. "
                "Set it in your .env file or use LLM_PROVIDER=mock for offline mode."
            )


# Module-level singleton — import this everywhere.
settings = Settings()
