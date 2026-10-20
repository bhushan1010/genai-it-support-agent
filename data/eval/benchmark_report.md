> Historical report: next-section scores describe the previous direct-section policy. Numbered runbooks now start at Step 1. Retrieval scores are unchanged; procedure-selection scores need a new sequence-aware evaluation.

# Local benchmark results

Draft development labels; not independent validation. 32 calibration cases; 28 held-out cases.

| Mode | Source hits | Avoidable refusal | Uncovered abstentions | Next section matches |
|---|---:|---:|---:|---:|
| keyword | 25/25 | 0 | 2/3 | 13/20 |
| semantic | 25/25 | 0 | 3/3 | 19/20 |
| hybrid | 25/25 | 0 | 3/3 | 19/20 |

Recommended configuration, chosen on calibration data only:
```json
{
  "retrieval_mode": "semantic",
  "retrieval_top_k": 1,
  "retrieval_score_threshold": 0.7
}
```

## Failed targeted cases
- keyword: `common-KB-NET-002-6`; proposed: Step 5 — Check the VPN server address.
- keyword: `common-KB-AUTH-001-5`; proposed: Self-service password reset (SSPR).
- keyword: `common-KB-APP-001-4`; proposed: Error: "Application failed to start" or "DLL not found".
- keyword: `common-KB-APP-001-5`; proposed: Error: Application crashes immediately or freezes.
- keyword: `common-KB-HW-001-4`; proposed: Step 6 — Check hardware health.
- keyword: `partial-KB-APP-001-3`; proposed: Error: "Application failed to start" or "DLL not found".
- keyword: `partial-KB-HW-001-3`; proposed: Step 6 — Check hardware health.
- keyword: `out-of-scope-3`; proposed: Step 6 — Check hardware health.
- semantic: `common-KB-AUTH-001-5`; proposed: Self-service password reset (SSPR).
- hybrid: `common-KB-AUTH-001-5`; proposed: Self-service password reset (SSPR).

## Limits
- Draft labels need independent human review; preliminary held-out outputs were inspected during development.
- No paid generation or LLM judge used.
- Latency excludes model load and includes cached-query effects.
- Timed human resolution comparison has not been run.
- Traceability verifies extraction, not correctness of runbooks or applicability.
- All emitted steps were mechanically traceable to complete source sections. This does not prove applicability.
