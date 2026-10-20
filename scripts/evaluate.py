"""Evaluation script for the IT Support Agent.

Measures:
  - Retrieval hit rate (Recall@k): whether the expected source doc_id
    appears in the top-k retrieved chunks.
  - Abstention accuracy: whether the agent correctly abstains for
    questions that should not be answered.
  - Classification accuracy against expected categories.

Usage:
    python scripts/evaluate.py

Output: a per-question breakdown and JSON summary in data/eval/eval_results.json.

Note: This script tests retrieval deterministically. It does NOT use an
LLM for evaluation metrics, so it runs without an API key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.rag.embeddings import get_embedding_provider
from app.rag.retriever import Retriever
from app.services.classifier import classify

configure_logging("WARNING")  # Suppress INFO during evaluation
logger = get_logger("evaluate")

EVAL_SET_PATH = Path("data/eval/eval_set.json")


def run_evaluation() -> None:
    print("=" * 60)
    print("IT Support Agent — Evaluation")
    print("=" * 60)

    # Load eval set
    if not EVAL_SET_PATH.exists():
        print(f"ERROR: Eval set not found at {EVAL_SET_PATH}")
        sys.exit(1)

    with open(EVAL_SET_PATH, encoding="utf-8") as f:
        eval_data = json.load(f)

    questions = eval_data["questions"]
    print(f"Loaded {len(questions)} evaluation question(s).")

    # Initialise retriever
    embedding_provider = get_embedding_provider(
        settings.embedding_provider, settings.embedding_model
    )
    try:
        retriever = Retriever(
            store_path=settings.vector_store_path,
            collection_name=settings.vector_store_collection,
            embedding_provider=embedding_provider,
            top_k=settings.retrieval_top_k,
            score_threshold=settings.retrieval_score_threshold,
        )
    except Exception as exc:
        print(f"ERROR: Cannot open vector store: {exc}")
        print("Run 'python scripts/ingest.py' first.")
        sys.exit(1)

    results = []
    retrieval_hits = 0
    abstention_correct = 0
    classification_correct = 0
    answerable_count = 0
    abstention_count = 0

    print()
    print(f"{'ID':<12} {'Cat match':<12} {'Retrieval':<12} {'Abstention':<12} Question")
    print("-" * 80)

    for q in questions:
        qid = q["id"]
        question = q["question"]
        expected_sources = q.get("expected_sources", [])
        expected_category = q.get("category", "")
        expects_abstention = q.get("expects_abstention", False)

        # Classification
        classification = classify(question)
        cat_match = classification.category.value == expected_category

        # Retrieval
        chunks = retriever.retrieve(question)
        retrieved_doc_ids = {c.doc_id for c in chunks}

        retrieval_hit = False
        abstention_ok = None

        if expects_abstention:
            abstention_count += 1
            abstention_ok = len(chunks) == 0
            if abstention_ok:
                abstention_correct += 1
            retrieval_hit_str = "—"
            abstention_str = "✓" if abstention_ok else "✗"
        else:
            answerable_count += 1
            if expected_sources:
                retrieval_hit = any(src in retrieved_doc_ids for src in expected_sources)
            else:
                retrieval_hit = len(chunks) > 0
            if retrieval_hit:
                retrieval_hits += 1
            retrieval_hit_str = "✓" if retrieval_hit else "✗"
            abstention_str = "—"

        if cat_match:
            classification_correct += 1

        row = {
            "id": qid,
            "question": question,
            "expected_category": expected_category,
            "predicted_category": classification.category.value,
            "category_match": cat_match,
            "expected_sources": expected_sources,
            "retrieved_doc_ids": sorted(retrieved_doc_ids),
            "retrieval_hit": retrieval_hit,
            "expects_abstention": expects_abstention,
            "abstention_correct": abstention_ok,
            "chunks_retrieved": len(chunks),
        }
        results.append(row)
        cat_str = "✓" if cat_match else "✗"
        print(f"{qid:<12} {cat_str:<12} {retrieval_hit_str:<12} {abstention_str:<12} {question[:42]}")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total = len(questions)
    print(f"Total questions:          {total}")
    print(f"Classification correct:   {classification_correct}/{total} "
          f"({100*classification_correct//total}%)")
    if answerable_count:
        print(f"Retrieval Recall@{settings.retrieval_top_k}:       "
              f"{retrieval_hits}/{answerable_count} "
              f"({100*retrieval_hits//answerable_count}%)")
    if abstention_count:
        print(f"Abstention accuracy:      {abstention_correct}/{abstention_count} "
              f"({100*abstention_correct//abstention_count}%)")
    print()
    print("NOTE: Retrieval metrics are deterministic (no LLM used).")
    print("NOTE: Answer quality requires human review.")
    print("=" * 60)

    # Write JSON results
    out_path = Path("data/eval/eval_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": {
                    "total": total,
                    "classification_correct": classification_correct,
                    "retrieval_hits": retrieval_hits,
                    "answerable_count": answerable_count,
                    "abstention_correct": abstention_correct,
                    "abstention_count": abstention_count,
                },
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"Full results written to: {out_path}")


if __name__ == "__main__":
    run_evaluation()
