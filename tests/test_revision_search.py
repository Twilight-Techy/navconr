import sqlite3

import pytest

from navconr import Index, NavconrError


def legacy_snapshot(index, destination):
    """Create the previous on-disk layout without changing source records or snapshots."""
    index.store.backup(destination)
    with sqlite3.connect(destination) as connection:
        connection.execute(
            "CREATE VIRTUAL TABLE search USING fts5(revision UNINDEXED,node UNINDEXED,title,text,tokenize='unicode61')"
        )
        for (revision,) in connection.execute("SELECT id FROM revisions").fetchall():
            table = index.store.search_table(revision)
            connection.execute(
                f"INSERT INTO search SELECT ?,node,title,text FROM {table}", (revision,)
            )
            connection.execute(f"DROP TABLE {table}")
        connection.execute("PRAGMA user_version=1")


def test_retained_revisions_cannot_change_pinned_search_scores(index, corpus):
    session = index.session()
    before = session.engine.lexical("refresh tokens expire")
    for i in range(20):
        (corpus / f"new-{i}.md").write_text("# New source\n\n" + "tokens refresh " * (i + 1))
    index.ingest(corpus)
    assert session.engine.lexical("refresh tokens expire") == before
    reopened = index.session(session.data.revision)
    assert reopened.engine.lexical("refresh tokens expire") == before


def test_v1_migration_preserves_evidence_and_scoped_search(index, tmp_path):
    original = index.session()
    ranking = original.engine.lexical("tokens")
    path = tmp_path / "legacy.sqlite"
    legacy_snapshot(index, path)
    with Index(path) as migrated:
        assert migrated.store.db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert migrated.store.verify()["integrity"] == "ok"
        assert migrated.session().engine.lexical("tokens") == ranking
        assert migrated.store.load().revision == original.data.revision


def test_failed_migration_rolls_back_without_losing_legacy_data(index, tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite"
    legacy_snapshot(index, path)
    connect = sqlite3.connect

    def deny_new_tables(*args, **kwargs):
        connection = connect(*args, **kwargs)
        connection.set_authorizer(
            lambda action, *_: (
                sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_CREATE_VTABLE else sqlite3.SQLITE_OK
            )
        )
        return connection

    monkeypatch.setattr(sqlite3, "connect", deny_new_tables)
    with pytest.raises(NavconrError, match="rolled back"):
        Index(path)
    with connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM search").fetchone()[0] > 0
