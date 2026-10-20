# Evaluation artifacts

- `benchmark_v2.json`: 60 draft, source-labelled scenarios; 32 calibration / 28 held out.
- `benchmark_report.json`: complete local comparison, configurations, source hashes and failures.
- `benchmark_report.md`: compact results with denominators and limitations.
- `demo_transcript.md`: actual cached-model API smoke output using free extracts.
- `human_review.csv`: blank independent review scores, one row per scenario.
- `timed_study.csv`: blank real-world study inputs. No timing result has been claimed.
- `eval_set.json`: original 10-case legacy vector-store evaluation; retained for compatibility.

Run `python scripts/benchmark.py` to reproduce the comparison using cached local model files.
See `docs/EVALUATION.md` for label provenance, metric definitions, caveats and human protocol.
No paid API calls are made. Do not treat the agent-authored labels as independent validation.
