# Source coordinates, identity, and updates

Original blobs are immutable bytes addressed by SHA-256. Text spans use zero-based, end-exclusive byte offsets. Display lines are one-based inclusive. UTF-8 decoding occurs only after slicing and rejects boundaries that split a code point. Original CRLF bytes are retained. Repeated text is disambiguated by offset rather than text search. Empty sources have a valid zero-length span.

PDF, DOCX, HTML and notebook extraction produces separate content-addressed UTF-8 artifacts. Each artifact records its original source blob and an origin label (for example page:3 or cell:2). Returned evidence identifies whether its coordinates refer to original or extracted bytes. An extracted passage is not represented as an original binary byte interval. Extraction text may differ between extractor versions; parser fingerprints invalidate prior caches.

Source paths are relative to an explicitly configured root. Discovery rejects symlinks leaving the root and excludes runtime/cache folders. Imports and document links cannot widen that root. Published index revisions are immutable membership sets. Queries pin a revision; cursors cannot migrate between revisions or operations.

Node IDs include source and content structure identity; arbitrary edits need not preserve them. Span IDs include source, blob and interval. Same bytes at distinct source paths retain distinct logical references. Renames create a new path identity and report a unique same-hash previous path as a rename candidate, not a guaranteed logical match. Old citations remain valid in retained revisions. Deletion removes current membership without invalidating retained history.

Snapshots retained by a run must be pinned. Garbage collection removes only noncurrent, unpinned revisions and then unreferenced objects. Backup uses SQLite's backup API; restore validates schema and foreign references before use. Index publication and the current pointer change share one transaction.
