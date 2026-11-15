from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from .budget import Budget
from .ingestion import Enricher, ingest
from .models import Card, Edge, Event, Evidence, Limits, NavconrError, Node, Page, ReadItem, Span
from .search import Encoder, Search
from .storage import Store
from .util import exact_slice, identity


class Index:
    def __init__(self, path: str | Path):
        self.store = Store(path)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self) -> None:
        self.store.close()

    def ingest(
        self, root: str | Path, *, block_bytes: int = 2048, enricher: Enricher | None = None
    ):
        return ingest(self.store, root, block_bytes=block_bytes, enricher=enricher)

    def session(
        self,
        revision: str | None = None,
        limits: Limits | None = None,
        encoder: Encoder | None = None,
    ) -> Session:
        return Session(self.store, revision, Budget(limits), encoder)

    def overview(self, **kwargs):
        return self.session().overview(**kwargs)

    def search(self, query, **kwargs):
        return self.session().search(query, **kwargs)

    def expand(self, node_ids, **kwargs):
        return self.session().expand(node_ids, **kwargs)

    def follow(self, node_id, **kwargs):
        return self.session().follow(node_id, **kwargs)

    def read(self, span_ids, **kwargs):
        return self.session().read(span_ids, **kwargs)

    def link(self, edges: list[Edge]):
        session = self.session()
        data = session.data.model_copy(deep=True)
        existing = {edge.model_dump_json() for edge in data.edges}
        original_count = len(existing)
        for edge in edges:
            session.add_relationship(edge)
            if edge.model_dump_json() not in existing:
                data.edges.append(edge)
                existing.add(edge.model_dump_json())
        if len(existing) == original_count:
            return session.data
        data.revision = identity(data.revision, "relationships", sorted(existing))
        self.store.publish(data, {})
        return data

    def group(self, title: str, node_ids: list[str]):
        if not title.strip() or len(title) > 160 or not node_ids:
            raise NavconrError("group requires a bounded title and at least one member")
        session = self.session()
        for nid in node_ids:
            session.node(nid)
        data = session.data.model_copy(deep=True)
        nid = identity("semantic-group", title, sorted(set(node_ids)))
        if nid in data.nodes:
            return data
        data.nodes[nid] = Node(
            id=nid,
            title=title,
            kind="group",
            summary=" | ".join(session.node(item).title for item in node_ids)[:600],
        )
        data.edges.append(Edge(source="root", target=nid, relation="semantic", origin="manual"))
        data.edges.extend(
            Edge(source=nid, target=member, relation="member", origin="manual")
            for member in sorted(set(node_ids))
        )
        data.revision = identity(data.revision, nid)
        self.store.publish(data, {})
        return data

    def group_topics(self):
        """Deterministic topic maps from shared headings across different sources."""
        from .util import slug

        session = self.session()
        data = session.data.model_copy(deep=True)
        topics: dict[str, list[Node]] = {}
        for node in data.nodes.values():
            if node.kind == "section":
                topics.setdefault(slug(node.title), []).append(node)
        added = 0
        for topic, members in sorted(topics.items()):
            if not topic or len({node.source for node in members}) < 2:
                continue
            nid = identity("heading-topic", topic, sorted(node.id for node in members))
            if nid in data.nodes:
                continue
            data.nodes[nid] = Node(
                id=nid,
                title=members[0].title,
                kind="group",
                summary=f"Shared heading across {len(members)} source sections",
            )
            data.edges.append(Edge(source="root", target=nid, relation="semantic", origin="manual"))
            data.edges.extend(
                Edge(source=nid, target=node.id, relation="member", origin="manual")
                for node in members
            )
            added += 1
        if added:
            data.revision = identity(data.revision, "heading-topics", sorted(data.nodes))
            self.store.publish(data, {})
        return data


class Session:
    def __init__(self, store: Store, revision: str | None, budget: Budget, encoder: Encoder | None):
        self.store = store
        self.data = store.load(revision)
        self.budget = budget
        self.engine = Search(store, self.data, encoder)
        self.events: list[Event] = []
        self.children: dict[str | None, list[str]] = {}
        for node in self.data.nodes.values():
            self.children.setdefault(node.parent, []).append(node.id)
        self.members: dict[str, list[str]] = {}
        for edge in self.data.edges:
            if edge.relation == "member" and edge.target:
                self.members.setdefault(edge.source, []).append(edge.target)

    def card(self, nid: str, score: float | None = None) -> Card:
        node = self.node(nid)
        return Card(
            id=node.id,
            title=node.title,
            summary=node.summary,
            kind=node.kind,
            children=len(self.children.get(nid, [])) + len(self.members.get(nid, [])),
            span_ids=node.span_ids,
            source=node.source,
            score=score,
            parent=node.parent,
        )

    def node(self, nid: str):
        if nid not in self.data.nodes:
            raise NavconrError(f"unknown node in revision {self.data.revision}: {nid}")
        return self.data.nodes[nid]

    def _record(self, action: str, arguments: dict, response: dict, started: float):
        self.events.append(
            Event(
                sequence=len(self.events),
                action=action,
                arguments=arguments,
                response=response,
                elapsed_ms=(time.monotonic() - started) * 1000,
                usage=self.budget.usage.model_copy(deep=True),
            )
        )

    def _page(
        self,
        action: str,
        arguments: dict,
        entries: list[tuple[str | None, float | None, str | None]],
        limit: int,
        cursor: str | None,
        max_bytes: int,
        expansion: int = 0,
    ) -> Page:
        started = time.monotonic()
        if not 1 <= limit <= 100 or not 512 <= max_bytes <= 65536:
            raise NavconrError("limit must be 1..100 and max_bytes 512..65536")
        fingerprint = identity(action, arguments, limit, max_bytes, self.data.revision)
        offset = 0
        if cursor:
            try:
                decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if decoded["fingerprint"] != fingerprint:
                    raise ValueError("cursor belongs to another operation or revision")
                offset = decoded["offset"]
                if not isinstance(offset, int) or not 0 <= offset <= len(entries):
                    raise ValueError("invalid cursor position")
            except (ValueError, KeyError, TypeError) as exc:
                raise NavconrError(f"invalid cursor: {exc}") from exc
        self.budget.charge(steps=1, expansions=expansion)
        page = Page(revision=self.data.revision, items=[])
        position = offset
        while position < len(entries) and position - offset < limit:
            nid, score, unresolved = entries[position]
            candidate = page.model_copy(deep=True)
            if nid:
                candidate.items.append(self.card(nid, score))
            elif unresolved:
                candidate.unresolved.append(unresolved)
            position += 1
            candidate.next_cursor = (
                base64.urlsafe_b64encode(
                    json.dumps({"fingerprint": fingerprint, "offset": position}).encode()
                ).decode()
                if position < len(entries)
                else None
            )
            size = len(candidate.model_dump_json().encode())
            remaining = self.budget.limits.map_bytes - self.budget.usage.map_bytes
            if size > min(max_bytes, remaining):
                position -= 1
                if position == offset:
                    raise NavconrError(
                        "map item exceeds response capacity; increase map/max_bytes budget"
                    )
                break
            page = candidate
        if position < len(entries):
            page.next_cursor = base64.urlsafe_b64encode(
                json.dumps({"fingerprint": fingerprint, "offset": position}).encode()
            ).decode()
        self.budget.charge(map_bytes=len(page.model_dump_json().encode()))
        self._record(
            action, {**arguments, "cursor": cursor, "limit": limit}, page.model_dump(), started
        )
        return page

    def overview(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        max_bytes: int = 16384,
        view: str = "physical",
    ) -> Page:
        if view not in {"physical", "semantic"}:
            raise NavconrError("overview view must be physical or semantic")
        entries = (
            self.children.get("root", [])
            if view == "physical"
            else [
                edge.target
                for edge in self.data.edges
                if edge.source == "root" and edge.relation == "semantic" and edge.target
            ]
        )
        return self._page(
            "overview",
            {"view": view},
            [(n, None, None) for n in entries],
            limit,
            cursor,
            max_bytes,
        )

    def expand(
        self,
        node_ids: list[str],
        *,
        limit: int = 20,
        cursor: str | None = None,
        max_bytes: int = 16384,
    ) -> Page:
        if not 1 <= len(node_ids) <= 20:
            raise NavconrError("expand requires 1..20 node IDs")
        entries: list[tuple[str | None, float | None, str | None]] = []
        seen = set()
        for nid in node_ids:
            self.node(nid)
            members = [
                edge.target
                for edge in self.data.edges
                if edge.source == nid and edge.relation == "member" and edge.target
            ]
            for child in [*self.children.get(nid, []), *members]:
                if child not in seen:
                    entries.append((child, None, None))
                    seen.add(child)
        return self._page(
            "expand", {"node_ids": node_ids}, entries, limit, cursor, max_bytes, len(node_ids)
        )

    def search(
        self,
        query: str,
        *,
        mode: str = "lexical",
        scope: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
        max_bytes: int = 16384,
    ) -> Page:
        if not query.strip() or len(query) > 1000:
            raise NavconrError("query must contain 1..1000 characters")
        self.budget.check()
        ranking = self.engine.rank(query, mode)
        if scope:
            self.node(scope)
            allowed = set(self.descendants(scope))
            ranking = [(nid, score) for nid, score in ranking if nid in allowed]
        return self._page(
            "search",
            {"query": query, "mode": mode, "scope": scope},
            [(nid, score, None) for nid, score in ranking],
            limit,
            cursor,
            max_bytes,
        )

    def descendants(self, nid: str) -> list[str]:
        result, queue = [], [nid]
        while queue:
            current = queue.pop()
            result.append(current)
            queue.extend(reversed(self.children.get(current, [])))
        return result

    def follow(
        self,
        node_id: str,
        *,
        relation: str = "reference",
        inverse: bool = False,
        origin: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
        max_bytes: int = 16384,
    ) -> Page:
        self.node(node_id)
        entries: list[tuple[str | None, float | None, str | None]] = []
        for edge in self.data.edges:
            endpoint = edge.target if inverse else edge.source
            if (
                endpoint == node_id
                and edge.relation == relation
                and (origin is None or edge.origin == origin)
            ):
                entries.append(
                    (edge.source if inverse else edge.target, edge.score, edge.unresolved)
                )
        return self._page(
            "follow",
            {"node_id": node_id, "relation": relation, "inverse": inverse, "origin": origin},
            entries,
            limit,
            cursor,
            max_bytes,
            1,
        )

    def read(
        self, span_ids: list[str], *, ranges: dict[str, tuple[int, int]] | None = None
    ) -> list[ReadItem]:
        if not 1 <= len(span_ids) <= 20:
            raise NavconrError("read requires 1..20 span IDs")
        started = time.monotonic()
        self.budget.charge(steps=1)
        items = []
        for sid in span_ids:
            self.budget.check()
            span = self.data.spans.get(sid)
            if not span:
                items.append(ReadItem(id=sid, error="unknown span in pinned revision"))
                continue
            selected = span
            if ranges and sid in ranges:
                start, end = ranges[sid]
                if not span.start <= start <= end <= span.end:
                    items.append(ReadItem(id=sid, error="requested range outside span"))
                    continue
                raw = self.store.blob(span.blob)
                selected = Span(
                    **{
                        **span.model_dump(),
                        "start": start,
                        "end": end,
                        "line_start": raw[:start].count(b"\n") + 1,
                        "line_end": raw[: max(start, end - 1)].count(b"\n") + 1,
                    }
                )
            raw = self.store.blob(selected.blob)
            try:
                text = exact_slice(raw, selected.start, selected.end)
            except (ValueError, UnicodeDecodeError) as exc:
                items.append(ReadItem(id=sid, error=str(exc)))
                continue
            size = len(text.encode())
            if self.budget.usage.source_bytes + size > self.budget.limits.source_bytes:
                items.append(
                    ReadItem(
                        id=sid,
                        error="source_bytes budget insufficient; select an explicit smaller range",
                    )
                )
                continue
            self.budget.charge(source_bytes=size)
            items.append(
                ReadItem(
                    id=sid, evidence=Evidence(span=selected, text=text, revision=self.data.revision)
                )
            )
        # Account for metadata and error messages separately from exact evidence bytes.
        metadata_bytes = len(
            json.dumps([i.model_dump() for i in items], ensure_ascii=False).encode()
        ) - sum(len(i.evidence.text.encode()) for i in items if i.evidence)
        self.budget.charge(map_bytes=max(0, metadata_bytes))
        self._record(
            "read",
            {"span_ids": span_ids, "ranges": ranges},
            {"items": [i.model_dump() for i in items]},
            started,
        )
        return items

    def add_relationship(self, edge: Edge):
        """Validate candidate relationships before staging a new immutable revision."""
        self.node(edge.source)
        if edge.target:
            self.node(edge.target)
        elif not edge.unresolved:
            raise NavconrError(
                "relationship needs a resolved target or explicit unresolved reference"
            )
        if any(sid not in self.data.spans for sid in edge.evidence):
            raise NavconrError("relationship refers to missing evidence")
        return edge
