# Security and limitations

This is a local portfolio demo. It neither executes remediation nor manages accounts. The
sample runbooks are synthetic and require independent IT review before real-world use.

Default generation is free, verbatim extraction. Local semantic embeddings may download a
free model on first use; the benchmark requires cached weights and disables downloads. Paid
OpenAI generation is optional and was not used in the benchmark or demo validation.

Queries, history and outcomes are untrusted. The API validates roles, lengths and outcome
values. A procedure is identified by its source-content hash; foreign document IDs cannot
mark a different issue resolved. Outcomes are user assertions, not verified success. No
server persistence or identity/role system exists. Supervisor and manager access is future work.

Users should reset the session when changing issues. Browser-session data disappears on
reset or restart. Query excerpts are logged, so do not submit secrets, credentials, customer
information or confidential incidents. Optional paid generation transmits supplied context
and history to the configured provider; default extractive generation makes no paid call.

The evidence threshold is a heuristic. Normalized semantic similarity is not a confidence
probability. Source copying proves traceability, not policy correctness or safe applicability.
Full sections preserve warnings, but the application cannot verify whether each prerequisite
holds. Users must review the guidance and escalate when context is missing.

The benchmark has only five runbooks, draft labels and three uncovered held-out cases.
Preliminary held-out outputs were inspected during development. No independent accuracy
certification or faster-resolution result is claimed. Prompt-based optional LLM generation
is not a formal prompt-injection defense. Authentication, retention policies, audited access,
rate limiting and production hardening are not implemented.

## Uploaded rulebooks and public search

Uploads are request-scoped, limited to UTF-8 Markdown/text, and never written to server files.
Do not expose this unauthenticated demo to an untrusted network. Uploaded documents and history
are never sent to the search provider. Public search transmits a shortened search query with
common sensitive patterns removed; that is not a comprehensive data-loss-prevention system.
The UI provides an Internet fallback toggle. API clients must explicitly opt in.

The fallback allows only HTTPS `learn.microsoft.com/en-us/` documentation, excludes Q&A,
rejects redirects and URL credentials/nonstandard ports, limits page bytes and timeouts, and
does not execute HTML/JavaScript. It reads full fetched article bodies rather than answer
snippets. No answer is produced solely because a search result exists. Relevant local policy
text takes priority even without a procedure; local retrieval errors do not bypass policy.

Sources are analyzed using deterministic structure, origin and relevance checks plus local
embeddings when available. These do not establish factual correctness, detect all malicious
content or prove environmental applicability. Uploaded policy relationships and contradictions
require human review. The Learn search endpoint can change or become unavailable.
