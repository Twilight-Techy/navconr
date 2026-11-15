from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlsplit

from .models import Artifact, Edge, IndexData, NavconrError, Node, Source, Span
from .parsers import PARSER_VERSION, SUPPORTED, extract, outline, split_ranges, structure_breaks
from .storage import Store
from .util import digest, identity, slug

EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".navconr",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "_viewer",
}


class Enricher(Protocol):
    fingerprint: str

    def summarize(self, text: str) -> str: ...


def ingest(
    store: Store, root: str | Path, *, block_bytes: int = 2048, enricher: Enricher | None = None
) -> IndexData:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NavconrError("source root must be a directory")
    if not 64 <= block_bytes <= 65536:
        raise NavconrError("block_bytes must be between 64 and 65536")
    paths = []
    diagnostics = []
    for directory, child_dirs, file_names in os.walk(root, followlinks=False):
        child_dirs[:] = sorted(
            name for name in child_dirs if name not in EXCLUDED and not name.startswith(".")
        )
        for name in sorted(file_names):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if name.startswith(".") or path.suffix.lower() not in SUPPORTED or not path.is_file():
                continue
            if not path.resolve().is_relative_to(root):
                diagnostics.append(f"excluded symlink outside source root: {relative.as_posix()}")
                continue
            paths.append(path)
    paths.sort()
    blobs = {}
    sources = {}
    for path in paths:
        raw = path.read_bytes()
        key = digest(raw)
        blobs[key] = raw
        name = path.relative_to(root).as_posix()
        sources[name] = Source(path=name, blob=key, parser=PARSER_VERSION)
    versions = {}
    for package in [
        "markdown-it-py",
        "pypdf",
        "python-docx",
        "beautifulsoup4",
        "tree-sitter",
        "tree-sitter-typescript",
    ]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    fingerprint = identity(
        PARSER_VERSION, versions, block_bytes, getattr(enricher, "fingerprint", "extractive-1")
    )
    revision = identity(
        str(root), fingerprint, [(name, s.blob) for name, s in sources.items()], diagnostics
    )
    reusable: IndexData | None
    try:
        reusable = store.load()
        if reusable.fingerprint != fingerprint or reusable.root != str(root):
            reusable = None
    except NavconrError:
        reusable = None
    curated = bool(reusable and any(edge.origin != "parsed" for edge in reusable.edges))
    if (
        reusable
        and [(name, s.blob) for name, s in reusable.sources.items()]
        == [(name, s.blob) for name, s in sources.items()]
        and [note for note in reusable.diagnostics if note.startswith("excluded symlink")]
        == diagnostics
    ):
        return reusable
    if not curated:
        try:
            previous = store.load(revision)
        except NavconrError:
            previous = None
        if previous:
            with store.db:
                store.db.execute("INSERT OR REPLACE INTO meta VALUES('current',?)", (revision,))
            return previous
    nodes = {"root": Node(id="root", title=root.name or "Collection", kind="collection")}
    spans = {}
    edges = []
    artifacts: list[Artifact] = []
    references = []
    anchors = {}
    documents = {}

    def add_span(source, blob, start, end, raw, origin):
        sid = identity(source, blob, start, end, origin)
        spans[sid] = Span(
            id=sid,
            source=source,
            blob=blob,
            start=start,
            end=end,
            coordinate="extracted" if origin else "original",
            origin=origin,
            line_start=raw[:start].count(b"\n") + 1,
            line_end=raw[: max(start, end - 1)].count(b"\n") + 1,
        )
        return sid

    for name, source in sources.items():
        if reusable and name in reusable.sources and reusable.sources[name].blob == source.blob:
            source.media_type = reusable.sources[name].media_type
            local_nodes = {
                nid: node.model_copy(deep=True)
                for nid, node in reusable.nodes.items()
                if node.source == name
            }
            nodes.update(local_nodes)
            spans.update(
                {
                    sid: span.model_copy(deep=True)
                    for sid, span in reusable.spans.items()
                    if span.source == name
                }
            )
            artifacts.extend(
                artifact.model_copy(deep=True)
                for artifact in reusable.artifacts
                if artifact.source == name
            )
            for artifact in reusable.artifacts:
                if artifact.source == name:
                    blobs[artifact.blob] = store.blob(artifact.blob)
            for nid, node in local_nodes.items():
                if node.kind == "document":
                    documents[name] = nid
                if node.anchor:
                    anchors[(name, node.anchor)] = nid
            for edge in reusable.edges:
                if edge.source not in local_nodes:
                    continue
                if edge.relation == "next":
                    edges.append(edge.model_copy(deep=True))
                elif edge.reference:
                    references.append((name, edge.source, edge.reference))
            diagnostics.extend(
                note
                for note in reusable.diagnostics
                if note.startswith(f"{name}:") or note.startswith(f"whitespace-only range: {name}:")
            )
            continue
        raw = blobs[source.blob]
        parts, source.media_type, notes = extract(name, raw)
        diagnostics.extend(notes)
        doc_id = identity(name, source.blob, "document")
        documents[name] = doc_id
        nodes[doc_id] = Node(
            id=doc_id, title=name[-160:], kind="document", parent="root", source=name
        )
        anchor_counts: dict[str, int] = {}
        for part_number, part in enumerate(parts):
            content = part.data
            blob = digest(content)
            blobs[blob] = content
            if part.origin:
                artifacts.append(
                    Artifact(
                        blob=blob,
                        original=source.blob,
                        source=name,
                        origin=part.origin,
                        extractor=fingerprint,
                    )
                )
            headings, links, notes = outline(name, part)
            preferred_breaks = structure_breaks(name, part)
            diagnostics.extend(notes)
            unit_id = doc_id
            if part.origin and part.origin.startswith(("page:", "cell:")):
                unit_id = identity(name, blob, part_number, "unit")
                nodes[unit_id] = Node(
                    id=unit_id,
                    title=part.origin.replace(":", " ").capitalize(),
                    kind="section",
                    parent=doc_id,
                    source=name,
                )
            stack = [(0, unit_id)]
            boundaries = sorted(
                {
                    0,
                    len(content),
                    *[h.start for h in headings],
                    *[h.end for h in headings],
                    *[h.scope_end for h in headings if h.scope_end is not None],
                }
            )
            sections = {}
            for heading in headings:
                while stack[-1][0] >= heading.level:
                    stack.pop()
                nid = identity(name, blob, part_number, heading.start, "section")
                base_anchor = slug(heading.title)
                count = anchor_counts.get(base_anchor, 0)
                anchor_counts[base_anchor] = count + 1
                anchor = base_anchor + (f"-{count}" if count else "")
                sid = add_span(name, blob, heading.start, heading.end, content, part.origin)
                nodes[nid] = Node(
                    id=nid,
                    title=heading.title[:160],
                    kind="symbol"
                    if Path(name).suffix.lower() in {".py", ".ts", ".tsx"}
                    else "section",
                    parent=stack[-1][1],
                    span_ids=[sid],
                    source=name,
                    anchor=anchor,
                )
                anchors[(name, anchor)] = nid
                stack.append((heading.level, nid))
                sections[heading.start] = nid
            current_parent = unit_id
            block_ids = []
            for left, right in zip(boundaries, boundaries[1:], strict=False):
                if left in sections:
                    current_parent = sections[left]
                if any(heading.scope_end is not None for heading in headings):
                    active = [
                        heading
                        for heading in headings
                        if heading.scope_end is not None
                        and heading.start <= left < heading.scope_end
                    ]
                    current_parent = (
                        sections[
                            max(active, key=lambda heading: (heading.level, heading.start)).start
                        ]
                        if active
                        else unit_id
                    )
                for start, end in split_ranges(content, left, right, block_bytes, preferred_breaks):
                    text = content[start:end].decode("utf-8")
                    if not text.strip():
                        # Whitespace is included in adjacent raw spans where possible; explicit diagnostics account for gaps.
                        if start != end:
                            diagnostics.append(
                                f"whitespace-only range: {name}:{part.origin or 'original'}:{start}:{end}"
                            )
                        continue
                    sid = add_span(name, blob, start, end, content, part.origin)
                    nid = identity(name, blob, part_number, start, end, "block")
                    summary = text[:400]
                    if enricher:
                        cache_key = identity(fingerprint, digest(text.encode()))
                        cached = store.cache_get(cache_key)
                        if cached:
                            summary = cached["summary"]
                        else:
                            summary = enricher.summarize(text)
                            if not isinstance(summary, str) or len(summary) > 600:
                                raise NavconrError(
                                    "enricher returned an invalid or oversized summary"
                                )
                            store.cache_put(cache_key, {"summary": summary})
                    title = next(
                        (line.strip(" #\t\r") for line in text.splitlines() if line.strip()), name
                    )
                    nodes[nid] = Node(
                        id=nid,
                        title=title[:160],
                        summary=summary,
                        kind="block",
                        parent=current_parent,
                        span_ids=[sid],
                        source=name,
                    )
                    block_ids.append((start, end, nid))
            if not content:
                sid = add_span(name, blob, 0, 0, content, part.origin)
                nodes[unit_id].span_ids.append(sid)
            for (_, _, a), (_, _, b) in zip(block_ids, block_ids[1:], strict=False):
                edges.append(Edge(source=a, target=b, relation="next"))
            for offset, target in links:
                origin_node = next(
                    (nid for start, end, nid in block_ids if start <= offset < end), doc_id
                )
                references.append((name, origin_node, target))

    for name, origin, target in references:
        url = urlsplit(target)
        destination = unquote(url.path)
        candidate = (root / name).parent / destination if destination else root / name
        relation = "reference"
        if target.startswith("pyimport:"):
            relation = "imports"
            module = target[len("pyimport:") :]
            dots = len(module) - len(module.lstrip("."))
            base = (root / name).parent if dots else root
            for _ in range(max(0, dots - 1)):
                base = base.parent
            candidate = base / module.lstrip(".").replace(".", "/")
            options = [Path(str(candidate) + ".py"), candidate / "__init__.py"]
            resolved = next(
                (
                    documents.get(option.resolve().relative_to(root).as_posix())
                    for option in options
                    if option.resolve().is_relative_to(root)
                    and option.resolve().relative_to(root).as_posix() in documents
                ),
                None,
            )
        elif target.startswith("tsimport:"):
            relation = "imports"
            module = target[len("tsimport:") :]
            candidate = (root / name).parent / module
            options = (
                [
                    candidate,
                    Path(str(candidate) + ".ts"),
                    Path(str(candidate) + ".tsx"),
                    candidate / "index.ts",
                ]
                if module.startswith(".")
                else []
            )
            resolved = next(
                (
                    documents.get(option.resolve().relative_to(root).as_posix())
                    for option in options
                    if option.resolve().is_relative_to(root)
                    and option.resolve().relative_to(root).as_posix() in documents
                ),
                None,
            )
        elif url.scheme or url.netloc or not candidate.resolve().is_relative_to(root):
            resolved = None
        else:
            target_relative = candidate.resolve().relative_to(root).as_posix()
            resolved = (
                anchors.get((target_relative, unquote(url.fragment)))
                if url.fragment
                else documents.get(target_relative)
            )
        edges.append(
            Edge(
                source=origin,
                target=resolved,
                relation=relation,
                unresolved=None if resolved else target,
                reference=target,
            )
        )
    if reusable and curated:
        for old_node in reusable.nodes.values():
            if old_node.kind == "group":
                nodes[old_node.id] = old_node.model_copy(deep=True)
        for edge in reusable.edges:
            if edge.origin == "parsed":
                continue
            if edge.source not in nodes:
                diagnostics.append(
                    f"curated relationship source unavailable after update: {edge.source}"
                )
                continue
            kept = edge.model_copy(deep=True)
            if kept.target and kept.target not in nodes:
                kept.unresolved = f"stale-node:{kept.target}"
                kept.target = None
            kept.evidence = [sid for sid in kept.evidence if sid in spans]
            edges.append(kept)
        revision = identity(
            revision,
            "curated",
            [node.model_dump() for node in nodes.values() if node.kind == "group"],
            [edge.model_dump() for edge in edges if edge.origin != "parsed"],
        )
    child_nodes: dict[str | None, list[Node]] = {}
    for node in nodes.values():
        child_nodes.setdefault(node.parent, []).append(node)
    # Bottom-up, bounded extractive navigation summaries; full source remains separate.
    for node in reversed(list(nodes.values())):
        if node.kind not in {"block", "group"}:
            children = child_nodes.get(node.id, [])
            node.summary = " | ".join(n.title for n in children)[:600]
        if node.parent:
            edges.append(Edge(source=node.parent, target=node.id, relation="contains"))
    data = IndexData(
        revision=revision,
        root=str(root),
        fingerprint=fingerprint,
        sources=sources,
        artifacts=artifacts,
        spans=spans,
        nodes=nodes,
        edges=edges,
        diagnostics=diagnostics,
    )
    store.publish(data, blobs)
    return data


def changes(before: IndexData, after: IndexData) -> dict:
    old, new = before.sources, after.sources
    removed = sorted(old.keys() - new.keys())
    added = sorted(new.keys() - old.keys())
    renamed = []
    for name in added:
        candidates = [previous for previous in removed if old[previous].blob == new[name].blob]
        if len(candidates) == 1:
            renamed.append({"from": candidates[0], "to": name, "status": "candidate"})
    return {
        "added": added,
        "removed": removed,
        "modified": sorted(
            name for name in old.keys() & new.keys() if old[name].blob != new[name].blob
        ),
        "rename_candidates": renamed,
    }


def export_manifest(data: IndexData) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "revision": data.revision,
            "fingerprint": data.fingerprint,
            "sources": {k: v.blob for k, v in data.sources.items()},
        },
        indent=2,
    )
