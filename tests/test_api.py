"""Tests for the FastAPI routes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import pytest_asyncio
import httpx

from app.main import app
from app.services.classifier import ClassificationResult, TicketCategory


@pytest.fixture
def mock_app_state():
    """Set up mock application state for API tests."""
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "query": "My Wi-Fi is broken",
        "answer": "[MOCK] Try restarting the router.",
        "classification": ClassificationResult(
            category=TicketCategory.NETWORK_CONNECTIVITY,
            label="Network and Connectivity",
            confidence="high",
            method="rules",
            explanation="Matched 2 patterns.",
        ),
        "evidence_sufficient": True,
        "sources": [
            {
                "doc_id": "KB-NET-001",
                "source": "wifi_troubleshooting.md",
                "chunk_index": 0,
                "relevance_score": 0.85,
                "excerpt": "Check Device Manager...",
            }
        ],
        "needs_clarification": False,
    }

    mock_retriever = MagicMock()
    mock_retriever._collection.count.return_value = 42

    app.state.graph = mock_graph
    app.state.retriever = mock_retriever
    app.state.settings = MagicMock(llm_provider="mock")
    return mock_graph


@pytest_asyncio.fixture
async def client(mock_app_state):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as session:
        yield session


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "vector_store_docs" in data


@pytest.mark.asyncio
async def test_support_query_success(client):
    resp = await client.post("/api/v1/support", json={"query": "My Wi-Fi is not working."})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "category" in data
    assert "sources" in data


@pytest.mark.asyncio
async def test_support_query_too_short(client):
    resp = await client.post("/api/v1/support", json={"query": "hi"})
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_support_query_empty(client):
    resp = await client.post("/api/v1/support", json={"query": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_support_query_missing_body(client):
    resp = await client.post("/api/v1/support", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_support_query_no_graph():
    app.state.graph = None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as no_graph_client:
        resp = await no_graph_client.post("/api/v1/support", json={"query": "My Wi-Fi is not working."})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_api_forwards_history(client, mock_app_state):
    history = [{"role": "user", "content": "My Wi-Fi is broken"}]
    response = await client.post("/api/v1/support", json={"query": "Still broken", "conversation_history": history})
    assert response.status_code == 200
    assert mock_app_state.invoke.call_args.args[0]["conversation_history"] == history

@pytest.mark.asyncio
async def test_health_degraded_without_graph(client):
    app.state.graph = None
    response = await client.get("/api/v1/health")
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_api_accepts_session_rulebook_and_returns_its_procedure(client,mock_app_state):
    response=await client.post('/api/v1/support',json={'query':'orange printer jam','rulebooks':[{'name':'printer.md','content':'## Step 1 - Orange printer jam\n1. Open the orange printer tray.\n2. Check the paper jam.'}]})
    assert response.status_code==200
    result=response.json()
    assert result['knowledge_origin']=='uploaded_rulebook'
    assert result['answer_mode']=='extractive'
    assert result['sources'][0]['source']=='printer.md'
    assert result['steps'][0]['title']=='Step 1 - Orange printer jam'
    mock_app_state.invoke.assert_not_called()
