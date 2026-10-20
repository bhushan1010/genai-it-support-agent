"""Shared application exception hierarchy.

Keep exceptions specific enough to be caught selectively but general
enough to avoid explosion in the number of exception types.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors."""


class ConfigurationError(AppError):
    """Raised when a required configuration value is missing or invalid."""


class IngestionError(AppError):
    """Raised when document loading or indexing fails."""


class RetrievalError(AppError):
    """Raised when the vector-store query fails."""


class GenerationError(AppError):
    """Raised when LLM answer generation fails."""


class InsufficientEvidenceError(AppError):
    """Raised when retrieved evidence does not meet the confidence threshold.

    This is an expected, non-fatal condition in the workflow.
    """


class WorkflowError(AppError):
    """Raised when the LangGraph workflow encounters an unrecoverable state."""
