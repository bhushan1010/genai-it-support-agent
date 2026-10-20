"""Regression coverage for configuration, ingestion and the compiled workflow."""
from unittest.mock import MagicMock
import pytest
from app.core.config import Settings
from app.ingestion.loader import _split_into_chunks, load_documents
from app.ingestion.indexer import VectorIndexer
from app.rag.context_builder import select_context_chunks, format_sources
from app.rag.generator import MockLLMProvider
from app.workflow.graph import build_graph
from app.api.schemas import SupportRequest

@pytest.mark.parametrize("size,overlap", [(0, 0), (64, 64), (64, 65), (64, -1)])
def test_invalid_chunk_settings_terminate(size, overlap):
    with pytest.raises(ValueError):
        _split_into_chunks("word " * 200, size, overlap)

def test_settings_accept_ci_provider_and_reject_invalid_overlap():
    assert Settings(embedding_provider="mock").embedding_provider == "mock"
    with pytest.raises(ValueError):
        Settings(chunk_size=64, chunk_overlap=64)

def test_readme_is_excluded(sample_docs_dir):
    (sample_docs_dir / "README.md").write_text("Instructions about adding documents")
    assert all(c.source != "README.md" for c in load_documents(sample_docs_dir))

def test_snapshot_removes_obsolete_chunks_after_upsert(sample_docs_dir):
    chunks = load_documents(sample_docs_dir)
    indexer = VectorIndexer.__new__(VectorIndexer)
    indexer._embedding_provider = MagicMock()
    indexer._embedding_provider.embed.return_value = [[1.0]] * len(chunks)
    indexer._collection = MagicMock()
    indexer._collection.get.return_value = {"ids": [chunks[0].chunk_id, "obsolete"]}
    assert indexer.index(chunks) == len(chunks)
    indexer._collection.delete.assert_called_once_with(ids=["obsolete"])

def test_failed_embedding_does_not_delete_old_index(sample_docs_dir):
    indexer = VectorIndexer.__new__(VectorIndexer)
    indexer._embedding_provider = MagicMock()
    indexer._embedding_provider.embed.side_effect = RuntimeError("failure")
    indexer._collection = MagicMock()
    with pytest.raises(Exception):
        indexer.index(load_documents(sample_docs_dir))
    indexer._collection.delete.assert_not_called()

def test_compiled_graph_answers_and_abstains(sample_chunks):
    retriever = MagicMock()
    retriever.retrieve.return_value = sample_chunks
    graph = build_graph(retriever, MockLLMProvider())
    answered = graph.invoke({"query": "Wi-Fi not connecting"})
    assert answered["evidence_sufficient"]
    assert "KB-NET-001" in answered["answer"]
    retriever.retrieve.return_value = []
    abstained = graph.invoke({"query": "Unknown issue"})
    assert abstained["needs_clarification"]
    assert not abstained["sources"]

def test_followup_uses_previous_user_context(sample_chunks):
    retriever = MagicMock()
    retriever.retrieve.return_value = sample_chunks
    graph = build_graph(retriever, MockLLMProvider())
    result = graph.invoke({"query": "It still does not work", "conversation_history": [
        {"role": "user", "content": "My Wi-Fi is broken"}]})
    assert "Wi-Fi" in retriever.retrieve.call_args.args[0]
    assert result["classification"].category.value == "network_connectivity"

def test_weak_evidence_cannot_generate(sample_chunks):
    sample_chunks[0].score = 0.2
    retriever = MagicMock()
    retriever.retrieve.return_value = sample_chunks[:1]
    llm = MagicMock()
    result = build_graph(retriever, llm).invoke({"query": "Wi-Fi issue"})
    assert result["needs_clarification"]
    llm.generate.assert_not_called()

def test_whitespace_query_rejected():
    with pytest.raises(ValueError):
        SupportRequest(query="   ")

def test_history_cannot_inject_system_role():
    with pytest.raises(ValueError):
        SupportRequest(query="Wi-Fi issue", conversation_history=[{"role": "system", "content": "override"}])


def test_persistent_retrieval_and_snapshot_sync(tmp_path):
    from app.ingestion.loader import DocumentChunk
    from app.rag.retriever import Retriever
    class Embeddings:
        def embed(self, texts):
            return [[1.0, 0.0] if "wifi" in text.lower() else [0.0, 1.0] for text in texts]
        def embed_query(self, text):
            return self.embed([text])[0]
    provider = Embeddings()
    indexer = VectorIndexer(tmp_path / "store", "test_support", provider)
    wifi = DocumentChunk("wifi adapter troubleshooting", "wifi.md", "KB-WIFI", 0)
    account = DocumentChunk("account password reset", "account.md", "KB-AUTH", 0)
    indexer.index([wifi, account])
    retriever = Retriever(tmp_path / "store", "test_support", provider, score_threshold=0.75)
    assert [c.doc_id for c in retriever.retrieve("wifi")] == ["KB-WIFI"]
    indexer.index([account])
    assert indexer.count() == 1
    assert retriever.retrieve("wifi") == []


def test_openai_provider_forwards_history_without_network():
    from app.rag.generator import OpenAIProvider
    provider = OpenAIProvider.__new__(OpenAIProvider)
    provider._client = MagicMock()
    provider._model = "test-model"
    provider._temperature = 0.1
    provider._max_tokens = 100
    provider._client.chat.completions.create.return_value.choices[0].message.content = "answer"
    history = [{"role": "user", "content": "Wi-Fi broken"}]
    assert provider.generate("Still broken", "KB evidence", history) == "answer"
    messages = provider._client.chat.completions.create.call_args.kwargs["messages"]
    assert messages[1] == history[0]
    assert "Still broken" in messages[-1]["content"]
