# ADR 002: isolate FTS statistics by index revision

Status: implemented after isolated-install reproduction exposed a ranking difference.

The initial SQLite schema stored every revision in one FTS5 table and filtered query rows by revision. FTS5 BM25 statistics still covered the whole virtual table. Retained historical corpora therefore changed scores and evidence selection even for a pinned revision. The development database contained 540 search rows across retained revisions; the fresh reproduction contained 180. Evidence recall happened to match while selected evidence byte costs differed, so the full reproduction check correctly failed.

Database schema 2 uses one FTS5 virtual table per immutable revision. Names contain only a SHA-256 digest of the revision ID. Each table's document frequencies, average lengths and ranking are isolated from history. This favors correctness over deduplicating postings across equivalent map revisions.

The automatic schema 1→2 migration copies each revision's search rows into its own table, validates membership counts, drops the shared table and changes the schema version in one transaction. It preserves original blobs, revision IDs, record payloads and traces. A failed migration rolls back. Garbage collection drops the corresponding revision table. Record/tool/trace JSON schema remains version 1; database versioning is separate.

Regression tests require exact pinned scores before/after unrelated revisions, successful legacy migration with unchanged evidence, and rollback when new search tables cannot be created. The isolated-wheel experiment reproduction must compare evidence costs as well as recall after rebuilding artifacts.
