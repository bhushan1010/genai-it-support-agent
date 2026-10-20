# Evaluation protocol

Run `python scripts/benchmark.py` from the repository root. No API key or paid call is used.
The semantic and hybrid comparisons require the cached `all-MiniLM-L6-v2` model. The benchmark
sets offline mode and records unavailable modes instead of silently downloading or substituting
mock embeddings. The application may download that free model on its first semantic startup.

## Dataset and separation

`data/eval/benchmark_v2.json` contains 60 synthetic cases: 30 common incidents, 15 follow-ups,
10 partially covered requests and 5 uncovered requests. The calibration set has 32 cases; the
held-out set has 28. Follow-ups and partial variants stay with their parent scenario. The
implementation agent authored labels from these same five runbooks; **independent human review
has not occurred**. This is a small development benchmark, not external validation. Preliminary
held-out outputs were inspected during implementation; obtain a fresh human-authored test set
before making generalization claims.

Each label contains an exact source passage, expected document and (where applicable) section,
review status, and unsupported request. Follow-up cases additionally contain previous context
and an attempted section ID. Editing runbooks invalidates content-based step IDs; regenerate
and review affected cases rather than silently accepting outdated labels.

## Selection and metrics

Keyword, semantic and 50/50 hybrid search use identical full Markdown sections. Keyword scores
are `0.5 + 0.5 * IDF-weighted query-term coverage` (zero when no term matches); semantic scores
are `(1 + cosine) / 2`. Hybrid averages them. None is a correctness probability.

For each mode, sweep thresholds 0.55–0.9 and top-k 1/3/5 on calibration data only. Select by
`0.7 * source hit rate + 0.3 * out-of-scope abstention`, breaking ties by next-section match,
smaller k, then higher threshold. Choose the recommended mode using calibration results only.
Report the selected configuration and its held-out results, plus a fixed 0.6/top-5 baseline.

- Source hit rate: at least one expected document retrieved / answerable cases.
- Avoidable refusal: no evidence retrieved / answerable cases.
- Out-of-scope abstention: no evidence retrieved / uncovered cases.
- Next-section match: first proposed action matches the labelled section / targeted cases.
  Follow-ups without an exact next-section label are excluded from this metric.
- Verbatim traceability: emitted step text and ID match a runbook section. This is a mechanical
  extraction check; it does not establish correctness or suitability of the source guidance.
- Retrieval latency excludes model loading; warm-cache effects apply. Hardware and source
  hashes are saved with the JSON report.

See `data/eval/benchmark_report.md` and the per-case JSON, including failures. The initial
semantic configuration is top-k 1, threshold 0.7, selected using calibration cases.

## Human answer review

Use `data/eval/human_review.csv` with the answers in `benchmark_report.json`. Leave scores blank
until an IT reviewer has read the question, runbook and answer. Score 0 (wrong/missing), 1
(partial), or 2 (correct) for: correct next step, evidence support, usefulness, and appropriate
clarification/escalation. Flag any unsupported claim, missing prerequisite, invented URL,
misleading policy, unsafe applicability, or unnecessary repetition. Record reviewer and notes.
Review runbook accuracy separately: verbatim copying can faithfully reproduce a bad runbook.
No LLM judge is required.

## Timed comparison

Use `data/eval/timed_study.csv` to compare manual runbook lookup with the assistant. Assign
matched scenarios to each participant and counterbalance condition order; avoid showing the
same participant an identical question twice. Measure from seeing the question to selecting
the correct next step, not merely receiving any response. Record correctness and elapsed
seconds; never enter fabricated timings. Run `python scripts/summarize_study.py` for a summary.
The 20% improvement is a proposed target, **not a measured result**. Report sample size,
accuracy, unsuccessful trials, and paired timing differences before claiming faster resolution.
