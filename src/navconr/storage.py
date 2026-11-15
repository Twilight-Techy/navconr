from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import IndexData, NavconrError, Result
from .util import digest, exact_slice


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1, 2):
            self.db.close()
            raise NavconrError(f"unsupported database schema {version}; expected 2")
        if version == 0:
            if self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone():
                self.db.close()
                raise NavconrError(
                    "unversioned existing database requires an explicit migration; refusing to infer its schema"
                )
            self.db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE blobs(hash TEXT PRIMARY KEY, data BLOB NOT NULL);
                CREATE TABLE revisions(id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE runs(id TEXT PRIMARY KEY, revision TEXT NOT NULL REFERENCES revisions(id), data TEXT NOT NULL);
                CREATE TABLE pins(revision TEXT PRIMARY KEY REFERENCES revisions(id));
                CREATE TABLE cache(key TEXT PRIMARY KEY, data TEXT NOT NULL);
                PRAGMA user_version=2;
                COMMIT;
            """)
        elif version == 1:
            try:
                self._migrate_v1()
            except (sqlite3.Error, ValueError, NavconrError) as exc:
                self.db.close()
                raise NavconrError(
                    "database migration 1 to 2 failed and was rolled back; restore/inspect the original index"
                ) from exc

    @staticmethod
    def search_table(revision: str) -> str:
        # Only a hash is interpolated into SQL identifiers, never caller-supplied text.
        return "fts_" + digest(revision.encode())

    def _migrate_v1(self) -> None:
        try:
            self.db.execute("BEGIN IMMEDIATE")
            if self.db.execute("PRAGMA user_version").fetchone()[0] == 2:
                self.db.commit()
                return
            for revision, payload in self.db.execute("SELECT id,data FROM revisions").fetchall():
                data = IndexData.model_validate_json(payload)
                table = self.search_table(revision)
                self.db.execute(
                    f"CREATE VIRTUAL TABLE {table} USING fts5(node UNINDEXED,title,text,tokenize='unicode61')"
                )
                self.db.execute(
                    f"INSERT INTO {table}(node,title,text) SELECT node,title,text FROM search WHERE revision=?",
                    (revision,),
                )
                expected = sum(node.kind == "block" for node in data.nodes.values())
                if self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] != expected:
                    raise NavconrError("legacy search membership is inconsistent")
            self.db.execute("DROP TABLE search")
            self.db.execute("PRAGMA user_version=2")
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def close(self) -> None:
        self.db.close()

    def current(self) -> str:
        row = self.db.execute("SELECT value FROM meta WHERE key='current'").fetchone()
        if not row:
            raise NavconrError("index is empty; ingest a collection first")
        return row[0]

    def load(self, revision: str | None = None) -> IndexData:
        revision = revision or self.current()
        row = self.db.execute("SELECT data FROM revisions WHERE id=?", (revision,)).fetchone()
        if not row:
            raise NavconrError(f"unknown index revision: {revision}")
        return IndexData.model_validate_json(row[0])

    def blob(self, key: str) -> bytes:
        row = self.db.execute("SELECT data FROM blobs WHERE hash=?", (key,)).fetchone()
        if not row:
            raise NavconrError(f"missing snapshot {key}")
        value = bytes(row[0])
        if digest(value) != key:
            raise NavconrError(f"snapshot integrity failure: {key}")
        return value

    def validate(self, data: IndexData, blobs: dict[str, bytes]) -> None:
        if (
            "root" not in data.nodes
            or data.nodes["root"].kind != "collection"
            or data.nodes["root"].parent is not None
        ):
            raise NavconrError("index needs a valid collection root")
        if any(digest(value) != key for key, value in blobs.items()):
            raise NavconrError("snapshot hash mismatch")
        for span in data.spans.values():
            raw = blobs[span.blob] if span.blob in blobs else self.blob(span.blob)
            exact_slice(raw, span.start, span.end)
            if span.source not in data.sources:
                raise NavconrError("span has unknown source")
            if span.coordinate == "original" and span.blob != data.sources[span.source].blob:
                raise NavconrError("original span does not reference its original source blob")
            if span.coordinate == "extracted" and not any(
                a.blob == span.blob and a.source == span.source and a.origin == span.origin
                for a in data.artifacts
            ):
                raise NavconrError("extracted span has no matching extraction artifact")
        if any(key != span.id for key, span in data.spans.items()) or any(
            key != node.id for key, node in data.nodes.items()
        ):
            raise NavconrError("record key and record ID disagree")
        for source in data.sources.values():
            if source.blob not in blobs:
                self.blob(source.blob)
        for artifact in data.artifacts:
            if (
                artifact.source not in data.sources
                or artifact.original != data.sources[artifact.source].blob
            ):
                raise NavconrError("artifact original/source mismatch")
            if artifact.blob not in blobs:
                self.blob(artifact.blob)
        for node in data.nodes.values():
            if node.parent and node.parent not in data.nodes:
                raise NavconrError("node has unknown parent")
            if any(span_id not in data.spans for span_id in node.span_ids):
                raise NavconrError("node has unknown span")
            seen = {node.id}
            ancestor = node.parent
            while ancestor:
                if ancestor in seen:
                    raise NavconrError("physical hierarchy contains a cycle")
                seen.add(ancestor)
                ancestor = data.nodes[ancestor].parent
        for edge in data.edges:
            if edge.source not in data.nodes or (edge.target and edge.target not in data.nodes):
                raise NavconrError("relationship has unknown endpoint")
            if any(span not in data.spans for span in edge.evidence):
                raise NavconrError("relationship has unknown evidence")

    def publish(self, data: IndexData, blobs: dict[str, bytes]) -> None:
        self.validate(data, blobs)
        with self.db:
            for key, raw in blobs.items():
                self.db.execute("INSERT OR IGNORE INTO blobs VALUES(?,?)", (key, raw))
            payload = data.model_dump_json()
            existing = self.db.execute(
                "SELECT data FROM revisions WHERE id=?", (data.revision,)
            ).fetchone()
            if existing and existing[0] != payload:
                raise NavconrError("immutable revision collision")
            if not existing:
                self.db.execute("INSERT INTO revisions VALUES(?,?)", (data.revision, payload))
                table = self.search_table(data.revision)
                self.db.execute(
                    f"CREATE VIRTUAL TABLE {table} USING fts5(node UNINDEXED,title,text,tokenize='unicode61')"
                )
                for node in data.nodes.values():
                    if node.kind != "block":
                        continue
                    text = "\n".join(
                        exact_slice(blobs.get(s.blob) or self.blob(s.blob), s.start, s.end)
                        for sid in node.span_ids
                        for s in [data.spans[sid]]
                    )
                    self.db.execute(
                        f"INSERT INTO {table} VALUES(?,?,?)",
                        (node.id, node.title, text),
                    )
            self.db.execute("INSERT OR REPLACE INTO meta VALUES('current',?)", (data.revision,))

    def save_run(self, run: Result) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO runs VALUES(?,?,?)",
                (run.run_id, run.revision, run.model_dump_json()),
            )

    def run(self, run_id: str) -> Result:
        row = self.db.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise NavconrError("unknown run")
        return Result.model_validate_json(row[0])

    def cache_get(self, key: str) -> dict | None:
        row = self.db.execute("SELECT data FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key: str, value: dict) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO cache VALUES(?,?)", (key, json.dumps(value)))

    def backup(self, destination: str | Path) -> None:
        target = Path(destination)
        if target.resolve() == self.path.resolve() or target.exists():
            raise NavconrError("backup destination must be a new file")
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(target)
        try:
            self.db.backup(connection)
        finally:
            connection.close()

    def pin(self, revision: str) -> None:
        self.load(revision)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO pins VALUES(?)", (revision,))

    def gc(self) -> dict:
        retained = {self.current()}
        retained.update(row[0] for row in self.db.execute("SELECT revision FROM pins"))
        retained.update(row[0] for row in self.db.execute("SELECT DISTINCT revision FROM runs"))
        all_revisions = {row[0] for row in self.db.execute("SELECT id FROM revisions")}
        blobs: set[str] = set()
        for revision in retained:
            data = self.load(revision)
            blobs.update(s.blob for s in data.sources.values())
            blobs.update(a.blob for a in data.artifacts)
            blobs.update(s.blob for s in data.spans.values())
        with self.db:
            for revision in all_revisions - retained:
                self.db.execute(f"DROP TABLE IF EXISTS {self.search_table(revision)}")
                self.db.execute("DELETE FROM revisions WHERE id=?", (revision,))
            unused = {row[0] for row in self.db.execute("SELECT hash FROM blobs")} - blobs
            self.db.executemany("DELETE FROM blobs WHERE hash=?", [(key,) for key in unused])
        return {"removed_revisions": len(all_revisions - retained), "removed_blobs": len(unused)}

    def verify(self) -> dict:
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise NavconrError("SQLite integrity check failed")
        if self.db.execute("PRAGMA foreign_key_check").fetchall():
            raise NavconrError("foreign key check failed")
        count = 0
        for (revision,) in self.db.execute("SELECT id FROM revisions").fetchall():
            data = self.load(revision)
            self.validate(data, {})
            table = self.search_table(revision)
            try:
                rows = self.db.execute(f"SELECT node,title,text FROM {table}").fetchall()
            except sqlite3.Error as exc:
                raise NavconrError("revision search table is unavailable or corrupt") from exc
            blocks = {nid: node for nid, node in data.nodes.items() if node.kind == "block"}
            if len(rows) != len(blocks) or {row[0] for row in rows} != set(blocks):
                raise NavconrError("revision search membership is inconsistent")
            for nid, title, text in rows:
                node = blocks[nid]
                expected = "\n".join(
                    exact_slice(self.blob(span.blob), span.start, span.end)
                    for sid in node.span_ids
                    for span in [data.spans[sid]]
                )
                if title != node.title or text != expected:
                    raise NavconrError("search text does not match immutable source evidence")
            for source in data.sources.values():
                self.blob(source.blob)
            for span in data.spans.values():
                exact_slice(self.blob(span.blob), span.start, span.end)
            count += 1
        if count:
            self.load(self.current())
        return {"revisions": count, "integrity": "ok", "schema_version": 2}
