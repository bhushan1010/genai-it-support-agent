"""FastAPI application entry point.

Startup sequence:
  1. Load and validate configuration.
  2. Initialise logging.
  3. Load the embedding provider.
  4. Open the vector store (must be pre-indexed).
  5. Initialise the LLM provider.
  6. Build and compile the LangGraph workflow.
  7. Mount API routes.
"""

from __future__ import annotations

import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.exceptions import ConfigurationError, RetrievalError
from app.core.logging_config import configure_logging, get_logger
from app.rag.embeddings import get_embedding_provider
from app.rag.generator import get_llm_provider
from app.rag.retriever import Retriever
from app.workflow.graph import build_graph

configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title="GenAI IT Support Agent",
    description=(
        "A Retrieval-Augmented Generation agent that provides evidence-grounded "
        "IT troubleshooting guidance from a local knowledge base."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1", tags=["support"])


@app.on_event("startup")
async def startup() -> None:
    """Initialise all application components on startup."""
    logger.info("Starting GenAI IT Support Agent...")

    # Validate LLM config
    try:
        settings.validate_llm_config()
    except ValueError as exc:
        logger.warning("%s", exc)

    embedding_provider = None
    if settings.retrieval_mode != "keyword":
        embedding_provider = get_embedding_provider(settings.embedding_provider, settings.embedding_model)

    app.state.embedding_provider = embedding_provider

    # Retriever — may fail if the KB has not been indexed yet
    retriever = None
    try:
        if settings.retrieval_mode == "vectorstore":
            retriever = Retriever(settings.vector_store_path, settings.vector_store_collection,
                                  embedding_provider, settings.retrieval_top_k, settings.retrieval_score_threshold)
        else:
            from app.rag.local_support import SectionRetriever
            retriever = SectionRetriever(settings.docs_path, settings.retrieval_mode, embedding_provider,
                                         settings.retrieval_top_k, settings.retrieval_score_threshold)
        app.state.retriever = retriever
        logger.info("Retriever initialised.")
    except (RetrievalError, ValueError, OSError) as exc:
        logger.warning(
            "Retriever not available: %s. Run 'python scripts/ingest.py' first.", exc
        )
        app.state.retriever = None

    # LLM provider
    llm_provider = get_llm_provider(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_timeout,
    )

    # Build workflow graph (only if retriever is available)
    if retriever is not None:
        app.state.graph = build_graph(retriever, llm_provider)
        logger.info("LangGraph workflow ready.")
    else:
        app.state.graph = None
        logger.warning(
            "Workflow graph not built: retriever unavailable. "
            "Run ingestion then restart the server."
        )

    app.state.settings = settings
    logger.info("Startup complete. API listening on %s:%d", settings.app_host, settings.app_port)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
