# Product contract

Navconr serves application developers and agents researching technical knowledge collections. The first workflow indexes Markdown, shows a bounded map, explores relevant branches and references, and reads exact evidence. Example: find the refresh-token lifetime in authentication documentation and follow a link to the revocation procedure in operations documentation.

The full local release adds text-based PDFs, Python/TypeScript structure, HTML, DOCX, and notebooks; lexical/vector/hybrid retrieval; version-safe updates; traces; an inspector; CLI and MCP tools; reproducible evaluations. OCR, images, distributed storage, multi-tenant hosting, and learned policies are subsequent extensions.

Source means original immutable bytes. Artifact means a versioned extraction from a source. Span means an exact range in one source/artifact revision. Node means a navigation entry referencing zero or more spans. Evidence means source reads, never a generated summary. A map is a bounded set of node cards. A run is a revision-pinned sequence of recorded actions.

Public workflows must work without a model: ingest, inspect, search, follow, read, retrieve using a fixed lexical navigation policy, export, replay, evaluate, backup, and restore. A model policy is optional. Return explicit errors or stop reasons for invalid/stale references, unsupported inputs, absent evidence, exhausted budgets, deadlines, and provider failure. Never silently truncate evidence.

Release readiness requires documented limitations and validated artifacts. Publication identity, license, public destinations, third-party benchmark parity, human annotation review, and full research claims are separate gates; local functionality does not establish them.
