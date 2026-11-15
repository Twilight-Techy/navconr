# Data and tool contracts (schema 1)

The executable definitions live in `src/navconr/models.py`; `navconr schemas` exports JSON Schema. All stored records reject extra fields and carry a schema version. The store uses immutable revision membership and validates span/node/edge targets before atomically changing its current-revision pointer.

Sources contain a path, content hash and parser identity. Extracted artifacts preserve their original source hash and a mapping label (page, cell, or element). Spans identify the exact blob, coordinate space, byte interval and optional lines. Nodes carry bounded titles/summaries and a list of span IDs. Edges carry directed typed endpoints and origin; unresolved references carry an unresolved target string. Index revisions contain configuration/source fingerprints and a source root.

`overview`, `expand`, `search`, and `follow` return a Page of bounded cards, revision, and opaque continuation cursor. A cursor is tied to its operation, arguments, page sizing, and revision. A card exposes only IDs, bounded navigation text, kind, child count, and span IDs. `read` returns exact UTF-8 Evidence or an explicit per-item error. Oversized evidence requires an explicit smaller byte range; there is no implicit truncation.

Example span: `{id: s1, blob: <sha256>, source: docs/auth.md, start: 0, end: 12, coordinate: original, line_start: 1, line_end: 1}`. Example node: `{id: n1, title: Authentication, kind: section, span_ids: [s1]}`. IDs are validated against the chosen index revision. An end before start, unknown blob, non-UTF-8 boundary, unsupported version, or node pointing to an absent span is invalid.

Budgets are per-session shared ledgers. Tools charge serialized output bytes, expansions and steps; model calls additionally reserve input/output token capacity. Evidence byte budgets are exact. Token estimates are explicitly estimates. Strict model-token caps require a provider adapter with a declared trusted counting/capability contract. Unsupported strict caps fail before contacting the provider.

Controller results contain evidence, trace, usage and a stop reason. Trace schema 1 stores observed actions/results and errors, never hidden reasoning. Batch reads keep per-item outcomes. Sessions pin a revision even while a new index is published. Index operations are synchronous local work; `Navigator.retrieve` and provider operations are asynchronous and cancellable.
