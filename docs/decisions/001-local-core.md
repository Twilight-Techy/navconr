# ADR 001: local versioned core

Status: accepted working implementation direction, 2026-11-15.

Use Python 3.11+, Pydantic 2, markdown-it-py and SQLite FTS5. Keep original blobs in SQLite for atomicity and portable backup. Store immutable records with index-revision membership; the current pointer publishes in the same transaction. This prioritizes correctness and inspectability over distributed throughput. SQLite has one writer; no distributed-write guarantee is made.

Use one optional dependency extra per capability family. No model, frontend or framework is required by core ingestion/navigation. HTTP model adapters use async httpx; local tools are synchronous and invoked behind bounded sessions. CLI async entry points use `asyncio.run`; applications already in an event loop use `await`.

Provide a fixed lexical controller before model-directed actions. Search supports FTS5, reproducible TF-IDF cosine vectors (lexical, not semantic embeddings), reciprocal-rank hybrid, and an optional sentence-transformer encoder. Do not label TF-IDF as a learned semantic baseline. Source evidence always comes from exact reads.

Build the inspector separately, consuming a bounded local read-only API. Providers and integrations never execute retrieved instructions. Plaintext provider secrets are environment configuration and excluded from artifacts. Configured remote providers receive selected map/source content; the default path has no remote calls.

At the initial implementation decision, no public distribution license was inferred and local candidates recorded the license as unresolved. **Licensing update, 2026-11-15:** the user subsequently confirmed that Navconr is open source. MIT is now selected; see [LICENSE](../../LICENSE) and [release guidance](../RELEASE.md). Package publishing and paper submission still need concrete destinations and authorized account access.
