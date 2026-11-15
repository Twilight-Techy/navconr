import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from navconr import Index, Limits, NavconrError
from navconr.budget import Budget
from navconr.models import BudgetExceeded, Edge, Span
from navconr.util import exact_slice


def test_exact_original_unicode_crlf_and_disjoint_references(index, corpus):
    session = index.session()
    for span in session.data.spans.values():
        raw = (corpus / span.source).read_bytes()
        assert index.store.blob(span.blob) == raw
        assert session.read([span.id])[0].evidence.text.encode() == raw[span.start : span.end]
    node = next(
        n for n in session.data.nodes.values() if n.source == "unicode.md" and n.kind == "block"
    )
    span = session.data.spans[node.span_ids[0]]
    raw = index.store.blob(span.blob)
    mid = raw.find("é".encode()) + 1
    if mid > 0:
        assert session.read([span.id], ranges={span.id: (mid, span.end)})[0].error


def test_idempotent_ingestion_and_revision_isolation(index, corpus):
    old = index.session()
    assert index.ingest(corpus).revision == old.data.revision
    found = old.search("30 days").items[0]
    (corpus / "auth.md").write_text("# Authentication\nRefresh tokens expire after 90 days.\n")
    current = index.ingest(corpus)
    assert current.revision != old.data.revision
    assert "30 days" in old.read(found.span_ids)[0].evidence.text
    assert "90 days" in index.read(index.search("90 days").items[0].span_ids)[0].evidence.text


def test_failed_ingestion_is_atomic(index, corpus):
    current = index.store.current()
    (corpus / "bad.md").write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        index.ingest(corpus)
    assert index.store.current() == current


def test_links_and_unresolved_reference(index, corpus):
    session = index.session()
    refs = [e for e in session.data.edges if e.relation == "reference"]
    assert refs and refs[0].target
    assert session.follow(refs[0].source).items[0].title == "Revocation"
    with pytest.raises(NavconrError):
        session.add_relationship(
            Edge(source=refs[0].source, target="invented", relation="related", origin="inferred")
        )


def test_pagination_cursor_binding_and_bounds(index, corpus):
    session = index.session()
    page = session.overview(limit=1, max_bytes=4096)
    assert page.next_cursor
    next_page = session.overview(limit=1, max_bytes=4096, cursor=page.next_cursor)
    assert next_page.items[0].id != page.items[0].id
    with pytest.raises(NavconrError):
        session.search("tokens", cursor=page.next_cursor, limit=1, max_bytes=4096)
    with pytest.raises(NavconrError):
        session.overview(limit=0)
    with pytest.raises(NavconrError):
        session.overview(cursor="not-base64")


def test_reads_never_truncate(index):
    session = index.session(limits=Limits(source_bytes=1))
    card = session.search("30 days").items[0]
    result = session.read(card.span_ids)
    assert result[0].evidence is None
    assert "smaller range" in result[0].error
    assert session.budget.usage.source_bytes == 0


def test_budget_atomic_concurrent_reservations():
    budget = Budget(Limits(model_calls=100, model_tokens=100))

    def reserve(_):
        try:
            budget.reserve_model(40)
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(8))) == 2
    assert budget.usage.reserved_tokens == 80
    budget.reconcile_model(40, 20, measured=True)
    assert budget.usage.model_tokens == 20


def test_shared_tool_budget(index):
    session = index.session(limits=Limits(steps=1))
    session.overview()
    with pytest.raises(BudgetExceeded):
        session.search("tokens")


def test_symlink_root_boundary(index, corpus, tmp_path):
    secret = tmp_path / "outside.md"
    secret.write_text("private outside source")
    (corpus / "leak.md").symlink_to(secret)
    data = index.ingest(corpus)
    assert "leak.md" not in data.sources
    assert any("excluded symlink" in item for item in data.diagnostics)


def test_publish_validates_unknown_references_and_rolls_back(index):
    data = index.store.load().model_copy(deep=True)
    data.revision = "bad"
    data.nodes["root"].span_ids = ["missing"]
    with pytest.raises(NavconrError):
        index.store.publish(data, {})
    assert index.store.current() != "bad"


def test_snapshot_retention_backup_restore_gc(index, corpus, tmp_path):
    old = index.store.current()
    index.store.pin(old)
    (corpus / "ops.md").unlink()
    index.ingest(corpus)
    index.store.gc()
    assert index.store.load(old)
    destination = tmp_path / "backup.sqlite"
    index.store.backup(destination)
    with Index(destination) as restored:
        assert restored.store.verify()["integrity"] == "ok"
        assert restored.store.current() == index.store.current()
    with pytest.raises(NavconrError):
        index.store.backup(destination)


def test_model_schema_validation():
    with pytest.raises(ValidationError):
        Span(id="s", blob="b", source="a", start=10, end=5)
    with pytest.raises(ValidationError):
        Span(id="s", blob="b", source="a", start=0, end=0, invented="field")
    with pytest.raises(ValueError):
        exact_slice("é".encode(), 1, 2)


def test_search_modes(index):
    for mode in ["lexical", "vector", "hybrid"]:
        result = index.search("refresh tokens expire", mode=mode)
        assert result.items
        assert all(card.source == "auth.md" for card in result.items[:1])
    assert index.search("qzxnonexistent").items == []
    assert json.loads(index.overview().model_dump_json())["schema_version"] == 1


def test_unchanged_sources_reuse_parsing_and_links_retarget(index, corpus, monkeypatch):
    import navconr.ingestion as ingestion

    parsed = []
    original = ingestion.extract

    def tracked(name, raw):
        parsed.append(name)
        return original(name, raw)

    monkeypatch.setattr(ingestion, "extract", tracked)
    (corpus / "ops.md").write_text(
        "# Operations\n\n## Revocation\nRevoke by clearing the new session store.\n"
    )
    data = index.ingest(corpus)
    assert parsed == ["ops.md"]
    links = [edge for edge in data.edges if edge.relation == "reference"]
    assert links and links[0].target in data.nodes
    assert data.nodes[links[0].target].title == "Revocation"


def test_semantic_groups_and_inferred_edges_preserve_physical_tree(index):
    from navconr.enrichment import add_inferred_edges

    before = index.session()
    cards = before.search("tokens").items[:2]
    parents = {card.id: before.node(card.id).parent for card in cards}
    index.group("Token lifecycle", [card.id for card in cards])
    session = index.session()
    group = session.overview(view="semantic").items[0]
    assert group.kind == "group"
    assert {card.id for card in session.expand([group.id]).items} == set(parents)
    assert all(session.node(nid).parent == parent for nid, parent in parents.items())
    target = session.search("Redis").items[0]
    edge = Edge(
        source=cards[0].id,
        target=target.id,
        relation="related",
        origin="inferred",
        evidence=cards[0].span_ids,
    )
    add_inferred_edges(index, [edge])
    assert index.follow(cards[0].id, relation="related").items[0].id == target.id
    assert index.follow(cards[0].id, relation="related", origin="parsed").items == []
    assert index.follow(cards[0].id, relation="related", origin="inferred").items[0].id == target.id


def test_semantic_groups_survive_updates_with_explicit_stale_members(index, corpus):
    candidate = index.search("30 days").items[0]
    grouped = index.group("Lifetimes", [candidate.id])
    assert index.ingest(corpus).revision == grouped.revision
    (corpus / "auth.md").write_text("# Authentication\nChanged lifetime.\n")
    index.ingest(corpus)
    session = index.session()
    group = session.overview(view="semantic").items[0]
    response = session.follow(group.id, relation="member")
    assert response.unresolved == [f"stale-node:{candidate.id}"]


def test_unknown_database_schema_is_rejected(tmp_path):
    import sqlite3

    path = tmp_path / "future.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(NavconrError, match="schema"):
        Index(path)


def test_deterministic_topic_groups_span_multiple_sources(index, corpus):
    (corpus / "another.md").write_text(
        "# Other system\n\n## Refresh tokens\nAdditional refresh-token policy.\n"
    )
    index.ingest(corpus)
    data = index.group_topics()
    groups = index.session().overview(view="semantic").items
    assert groups
    group = next(card for card in groups if card.title == "Refresh tokens")
    assert len({item.source for item in index.expand([group.id]).items}) == 2
    assert index.group_topics().revision == data.revision


def test_integrity_check_rejects_a_dangling_current_revision(index):
    with index.store.db:
        index.store.db.execute("UPDATE meta SET value='missing' WHERE key='current'")
    with pytest.raises(NavconrError, match="unknown index revision"):
        index.store.verify()
