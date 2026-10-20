"""Ticket classification service.

Classifies user support queries into one of the defined IT support categories.

Implementation: rule-based offline fallback that matches keywords.
This is deterministic and runs without an LLM. If an LLM is available,
the workflow can optionally use it for richer classification, but the
rule-based fallback is always tested and should always produce a result.

Do not present keyword matching as semantic classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class TicketCategory(str, Enum):
    """Supported IT support ticket categories."""

    NETWORK_CONNECTIVITY = "network_connectivity"
    ACCOUNT_ACCESS = "account_access"
    SOFTWARE_INSTALLATION = "software_installation"
    APPLICATION_ERROR = "application_error"
    DEVICE_PERFORMANCE = "device_performance"
    GENERAL_IT = "general_it"
    UNKNOWN = "unknown"


CATEGORY_LABELS: dict[TicketCategory, str] = {
    TicketCategory.NETWORK_CONNECTIVITY: "Network and Connectivity",
    TicketCategory.ACCOUNT_ACCESS: "Account Access and Authentication",
    TicketCategory.SOFTWARE_INSTALLATION: "Software Installation or Configuration",
    TicketCategory.APPLICATION_ERROR: "Application Error",
    TicketCategory.DEVICE_PERFORMANCE: "Device and Performance Issues",
    TicketCategory.GENERAL_IT: "General IT Support",
    TicketCategory.UNKNOWN: "Unknown or Insufficient Information",
}

# Keyword patterns for each category (case-insensitive).
_RULES: list[tuple[TicketCategory, list[str]]] = [
    (
        TicketCategory.NETWORK_CONNECTIVITY,
        [r"wi.?fi", r"wireless", r"vpn", r"internet", r"network", r"connect",
         r"ip address", r"dns", r"ping", r"ethernet", r"proxy"],
    ),
    (
        TicketCategory.ACCOUNT_ACCESS,
        [r"password", r"locked", r"lockout", r"login", r"sign.?in", r"account",
         r"mfa", r"authenticat", r"credentials", r"reset", r"unlock"],
    ),
    (
        TicketCategory.SOFTWARE_INSTALLATION,
        [r"install", r"uninstall", r"software", r"licen[sc]e", r"activation",
         r"setup", r"deploy", r"update", r"upgrade", r"patch"],
    ),
    (
        TicketCategory.APPLICATION_ERROR,
        [r"crash", r"error", r"fail", r"not (launch|start|open)", r"dll",
         r"application", r"app", r"program", r"freeze", r"hang", r"exception"],
    ),
    (
        TicketCategory.DEVICE_PERFORMANCE,
        [r"slow", r"performance", r"cpu", r"memory", r"ram", r"disk", r"storage",
         r"battery", r"overheat", r"fan", r"boot", r"startup"],
    ),
]


@dataclass
class ClassificationResult:
    """Result of ticket classification."""

    category: TicketCategory
    label: str
    confidence: str   # 'high' | 'low' — deterministic, not a probability
    method: str       # 'rules' or 'llm'
    explanation: str


def classify(query: str) -> ClassificationResult:
    """Classify *query* using keyword rules.

    Returns a :class:`ClassificationResult`. The 'method' field is always
    'rules' for this implementation. Confidence is 'high' when at least
    two different patterns match, 'low' for a single match.

    Args:
        query: The user's IT support question (raw text).

    Returns:
        A classification result with a category, label, confidence, and
        a brief explanation of why this category was selected.
    """
    if not query.strip() or len(query.strip()) < 5:
        return ClassificationResult(
            category=TicketCategory.UNKNOWN,
            label=CATEGORY_LABELS[TicketCategory.UNKNOWN],
            confidence="low",
            method="rules",
            explanation="The query is too short or empty to classify.",
        )

    lowered = query.lower()
    scores: dict[TicketCategory, int] = {}

    for category, patterns in _RULES:
        matches = sum(1 for p in patterns if re.search(p, lowered))
        if matches:
            scores[category] = matches

    if not scores:
        logger.debug("No keyword match for query: %.60s", query)
        return ClassificationResult(
            category=TicketCategory.UNKNOWN,
            label=CATEGORY_LABELS[TicketCategory.UNKNOWN],
            confidence="low",
            method="rules",
            explanation=(
                "No IT support keywords were matched. "
                "The query may be out of scope or require clarification."
            ),
        )

    best_category = max(scores, key=lambda c: scores[c])
    match_count = scores[best_category]
    confidence = "high" if match_count >= 2 else "low"

    logger.debug(
        "Classified as %s (confidence=%s, matches=%d)",
        best_category.value, confidence, match_count
    )
    return ClassificationResult(
        category=best_category,
        label=CATEGORY_LABELS[best_category],
        confidence=confidence,
        method="rules",
        explanation=f"Matched {match_count} keyword pattern(s) for '{CATEGORY_LABELS[best_category]}'.",
    )
