"""Build the evidence context passed to the LLM.

The context is constructed from retrieved chunks so the LLM answer is
grounded in the retrieved knowledge base rather than the model's
pre-trained knowledge.
"""

from __future__ import annotations

from app.rag.retriever import RetrievedChunk

MAX_CONTEXT_WORDS = 1200  # Prevent excessively long prompts


def select_context_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    selected = []
    words = 0
    for chunk in chunks:
        size = len(chunk.text.split()) + 12
        if words + size > MAX_CONTEXT_WORDS and selected:
            break
        selected.append(chunk)
        words += size
    return selected


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered evidence block.

    Args:
        chunks: Chunks sorted by descending relevance.

    Returns:
        A formatted string suitable for inclusion in the LLM prompt.
    """
    if not chunks:
        return ""

    lines: list[str] = ["Retrieved knowledge-base evidence:\n"]
    word_count = 0

    for i, chunk in enumerate(select_context_chunks(chunks), start=1):
        header = f"[Source {i}: {chunk.doc_id} | {chunk.source} | relevance: {chunk.score:.2f}]"
        entry = f"{header}\n{chunk.text}"
        entry_words = len(entry.split())

        lines.append(entry)
        word_count += entry_words

    return "\n\n".join(lines)


def format_sources(chunks: list[RetrievedChunk]) -> list[dict]:
    """Return a serialisable list of source references for API responses."""
    seen: set[str] = set()
    sources: list[dict] = []
    for chunk in chunks:
        key = f"{chunk.doc_id}:{chunk.chunk_index}"
        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "doc_id": chunk.doc_id,
                    "url": chunk.url,
                    "fetched_at": chunk.fetched_at,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "relevance_score": chunk.score,
                    "excerpt": chunk.text[:300] + ("..." if len(chunk.text) > 300 else ""),
                }
            )
    return sources
