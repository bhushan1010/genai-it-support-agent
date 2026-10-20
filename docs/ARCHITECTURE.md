# Architecture

Streamlit sends a query, original issue, bounded message history and procedure outcomes to
FastAPI. LangGraph validates, classifies, retrieves, checks evidence and returns guidance.
The default extractive provider selects a complete verbatim Markdown section. The semantic
retriever embeds local runbook sections with all-MiniLM-L6-v2; the model is free and local.
Keyword and weighted hybrid search are alternative modes. Calibration-selected semantic
settings are top-k 1 and normalized similarity threshold 0.7.

Section IDs hash the document ID, heading and full section content. Outcomes are tried,
worked or did_not_work. IDs from other documents are ignored; previously attempted sections
are skipped. After targeted procedures are exhausted, selection follows the document order.
All completed procedures lead to the source escalation section; a reported success marks
that document's issue resolved. The application never independently verifies remediation.

The API is stateless. Session data is owned by Streamlit's current session and explicitly
reset for each new issue. This is not durable storage, authentication, or authorization.

Free answers expose one complete procedure, source references and outcome controls. They
include prerequisites and warnings rather than assembling isolated commands. Partial requests
receive only documented content and a scope clarification; there is no claim-level semantic
validator. Retrieval relevance does not prove answer correctness.

The original chunked ChromaDB ingestion and retriever remain optional via vectorstore mode.
The section workflow loads structured Markdown runbooks directly and needs no vectorstore
rebuild. Generation with OpenAI remains optional and has not been activated for this milestone.
