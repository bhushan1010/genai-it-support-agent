"""Tests for the ticket classification service."""

from __future__ import annotations

import pytest

from app.services.classifier import TicketCategory, classify


@pytest.mark.parametrize(
    "query, expected_category",
    [
        ("My Wi-Fi is not working", TicketCategory.NETWORK_CONNECTIVITY),
        ("VPN connection fails with authentication error", TicketCategory.NETWORK_CONNECTIVITY),
        ("My account is locked after wrong password", TicketCategory.ACCOUNT_ACCESS),
        ("I need to reset my password", TicketCategory.ACCOUNT_ACCESS),
        ("Application crashes with DLL error", TicketCategory.APPLICATION_ERROR),
        ("Software installation failed with license error", TicketCategory.SOFTWARE_INSTALLATION),
        ("Computer is slow and CPU is at 100%", TicketCategory.DEVICE_PERFORMANCE),
    ],
)
def test_classify_known_categories(query, expected_category):
    result = classify(query)
    assert result.category == expected_category


def test_classify_empty_query_returns_unknown():
    result = classify("")
    assert result.category == TicketCategory.UNKNOWN


def test_classify_too_short_returns_unknown():
    result = classify("hi")
    assert result.category == TicketCategory.UNKNOWN


def test_classify_no_keywords_returns_unknown():
    result = classify("The quick brown fox jumps over the lazy dog")
    assert result.category == TicketCategory.UNKNOWN


def test_classify_returns_label_string():
    result = classify("My internet is down")
    assert isinstance(result.label, str)
    assert len(result.label) > 0


def test_classify_method_is_rules():
    result = classify("My laptop is slow")
    assert result.method == "rules"


def test_classify_confidence_is_valid():
    result = classify("Wi-Fi not connecting to network")
    assert result.confidence in {"high", "low"}
