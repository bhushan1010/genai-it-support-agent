"""Streamlit chat-style IT support interface.

This UI calls the FastAPI backend at /api/v1/support. If the backend is
not running, it shows a clear error message.

Run with:
    streamlit run app/ui/streamlit_app.py
"""

from __future__ import annotations

import json
import os
from typing import Optional

import httpx
import streamlit as st

# — Configuration —
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
APP_TITLE = "GenAI IT Support Agent"
APP_SUBTITLE = "Evidence-grounded troubleshooting powered by RAG + LangGraph"

EXAMPLE_QUESTIONS = [
    "My laptop cannot connect to Wi-Fi after a Windows update.",
    "My account is locked after too many failed login attempts.",
    "I get an authentication failed error when connecting to VPN.",
    "An application says DLL not found when I try to launch it.",
    "My computer is running very slowly since this morning.",
    "The VPN client shows a certificate error. What does that mean?",
    "How do I reset my password without calling the helpdesk?",
    "My laptop fan is very loud and the device gets very hot.",
]


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# — Custom CSS: minimal, readable —
st.markdown(
    """
    <style>
    .source-card {
        background-color: #f0f4f8;
        border-left: 3px solid #4a90d9;
        padding: 0.5rem 0.8rem;
        border-radius: 4px;
        margin: 0.3rem 0;
        font-size: 0.85rem;
    }
    .mock-badge {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 0.3rem 0.6rem;
        border-radius: 4px;
        font-size: 0.82rem;
    }
    .disclaimer {
        color: #6c757d;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def check_backend_health() -> Optional[dict]:
    """Ping the backend health endpoint. Return the response dict or None."""
    try:
        resp = httpx.get(f"{API_BASE}/health", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def call_support_api(query: str) -> Optional[dict]:
    """Call the support endpoint and return the response dict or None."""
    try:
        resp = httpx.post(
            f"{API_BASE}/support",
            json={"query": query},
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json()
        st.error(f"API error {resp.status_code}: {resp.text}")
    except httpx.ConnectError:
        st.error(
            "🔴 Cannot reach the backend API. "
            f"Make sure the FastAPI server is running at {API_BASE}. "
            "Start it with: `uvicorn app.main:app --reload`"
        )
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
    return None


# — Sidebar —
with st.sidebar:
    st.title("🛡️ IT Support Agent")
    st.caption(APP_SUBTITLE)
    st.divider()

    health = check_backend_health()
    if health:
        st.success("✅ Backend online")
        st.metric("KB documents indexed", health.get("vector_store_docs", 0))
        llm = health.get("llm_provider", "unknown")
        if health.get("mock_mode"):
            st.markdown(
                '<div class="mock-badge">⚠️ Mock LLM mode — no real AI model</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(f"LLM: {llm}")
    else:
        st.error("🔴 Backend offline")
        st.info(
            "Start the API server:\n"
            "```\nuvicorn app.main:app --reload\n```"
        )

    st.divider()
    st.subheader("💬 Example questions")
    for q in EXAMPLE_QUESTIONS:
        if st.button(q, key=f"ex_{q[:30]}", use_container_width=True):
            st.session_state["pending_query"] = q

    st.divider()
    st.subheader("ℹ️ About")
    st.markdown(
        "**Stack:** Python · LangChain · LangGraph · ChromaDB · "
        "sentence-transformers · FastAPI · Streamlit\n\n"
        "**Mode:** Retrieval-Augmented Generation (RAG). Answers are grounded "
        "in the indexed knowledge base, not in general model knowledge.\n\n"
        "**Limitation:** This is a portfolio demonstration. Do not use for "
        "production IT operations."
    )


# — Main area —
st.title(f"🛡️ {APP_TITLE}")
st.caption(APP_SUBTITLE)
st.divider()

# Initialise session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"📚 {len(msg['sources'])} source(s) retrieved"):
                for src in msg["sources"]:
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>{src["doc_id"]}</strong> · {src["source"]} '
                        f'(chunk {src["chunk_index"]}, relevance: {src["relevance_score"]:.2f})<br>'
                        f'<em>{src["excerpt"][:200]}...</em>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# Handle pre-filled query from sidebar example buttons
input_query = st.session_state.pop("pending_query", None)

# Chat input
typed_query = st.chat_input("Describe your IT issue...")
query = typed_query or input_query

if query:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("🔍 Searching knowledge base and generating answer..."):
            response = call_support_api(query)

        if response:
            answer = response.get("answer", "No answer returned.")
            sources = response.get("sources", [])
            category = response.get("category", "")
            mock_mode = response.get("mock_mode", False)
            needs_clarification = response.get("needs_clarification", False)
            evidence_sufficient = response.get("evidence_sufficient", False)

            # Category badge
            st.caption(f"🏷️ Category: **{category}**")

            # Mock mode warning
            if mock_mode:
                st.markdown(
                    '<div class="mock-badge">⚠️ Mock LLM mode active — '
                    'configure LLM_PROVIDER=openai for real AI responses</div>',
                    unsafe_allow_html=True,
                )

            # Insufficient evidence warning
            if not evidence_sufficient:
                st.warning(
                    "⚠️ Limited knowledge-base evidence found. "
                    "The answer may be incomplete."
                )

            st.markdown(answer)

            # Sources
            if sources:
                with st.expander(f"📚 {len(sources)} source(s) retrieved"):
                    for src in sources:
                        st.markdown(
                            f'<div class="source-card">'
                            f'<strong>{src["doc_id"]}</strong> · {src["source"]} '
                            f'(chunk {src["chunk_index"]}, '
                            f'relevance: {src["relevance_score"]:.2f})<br>'
                            f'<em>{src["excerpt"][:200]}...</em>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            # Disclaimer
            disclaimer = response.get(
                "disclaimer",
                "AI-generated guidance. Review before applying.",
            )
            st.markdown(
                f'<p class="disclaimer">ℹ️ {disclaimer}</p>',
                unsafe_allow_html=True,
            )

            # Store in history
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                }
            )

# Clear button
if st.session_state.messages:
    if st.button("🗑️ Clear conversation", type="secondary"):
        st.session_state.messages = []
        st.rerun()
