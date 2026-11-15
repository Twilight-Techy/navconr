# Local operations and data handling

The initial deployment is a local library/CLI with one SQLite writer. Each revision stores a complete membership/metadata snapshot; original/extracted blobs are content-addressed and shared. Unchanged sources reuse parsing, spans and summaries. Current index metadata and FTS membership are rebuilt for each changed published revision. This is incremental source reuse, not a distributed or constant-time update guarantee.

Re-run ingest after additions, edits, deletions or renames. The CLI reports changes. Same-hash rename matches are candidates rather than guaranteed identity. Original evidence in retained revisions remains readable. Curated semantic groups persist; targets invalidated by edits are explicit stale-node references. Inferred relationships are not silently reasserted about changed content.

```bash
navconr verify --db .navconr/demo.sqlite
navconr backup snapshot.sqlite --db .navconr/demo.sqlite
navconr pin REVISION --db .navconr/demo.sqlite
navconr gc --db .navconr/demo.sqlite
```

Backup destinations must be new files. SQLite backup produces a consistent portable database. To restore, copy a verified backup to a new filename and run `navconr verify --db restored.sqlite` before using it. Never replace a live database connection's file. GC retains current revisions, explicit pins and every saved run's revision, then removes unreferenced blobs. This favors trace reproducibility; saved run retention is currently manual and can grow storage.

Database schema 0 means a new empty database and bootstraps to schema 2. Development schema 1 migrates transactionally to schema 2: each retained revision receives an isolated FTS5 table so historical corpora cannot affect its ranking statistics. Failed migration rolls back. Future/unknown versions and unversioned existing databases are rejected. Original snapshots, revision IDs and recorded traces survive migration. Record/tool JSON schema remains version 1. See ADR 002 for the isolated-install reproduction that exposed this issue.

Failed parsing, enrichment or validation cannot publish a partial revision. Valid enrichment cache entries may survive a failed attempt and be reused. A database integrity check verifies SQLite, record references, locators and blob hashes. Provider timeouts/retries stay inside the declared session limits; remote computation after disconnection is not observable.

Source root discovery prunes hidden paths, `.venv`, `.git`, `node_modules`, generated bundles, runtime directories and build outputs. Out-of-root symlink files are excluded. Local snapshot reads never fetch linked URLs or read arbitrary target paths. The inspector binds only to loopback, rejects foreign Host/Origin requests, and exposes bounded read endpoints without shell or write access. Do not expose it as a public authenticated service; that product is outside this release.

The default workflow sends no data to external models. Explicitly configured provider enrichment/navigation/answer calls send selected content to that endpoint. Traces can contain original source excerpts and queries. Store them as sensitive local data when the corpus is private. Source-omitting exports remove evidence bodies and summaries but still contain titles, paths, identifiers and relationship metadata; inspect them before sharing. No credential values belong in sources, traces, CI, or the release bundle.

See `reports/scale.json` for measured local scale behavior. Entire revision metadata is currently loaded into memory per session. Generated maps and tool responses are bounded; that does not imply sublinear host memory or query work. No million-document or distributed performance guarantee is made.
