from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from . import __version__, models
from .index import Index
from .ingestion import changes, export_manifest
from .models import Limits, NavconrError
from .navigation import Navigator
from .providers import OllamaProvider


def output(value):
    if isinstance(value, BaseModel):
        value = value.model_dump()
    print(json.dumps(value, indent=2, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    app = argparse.ArgumentParser(prog="navconr", description="Navigate maps; read exact evidence.")
    app.add_argument("--version", action="version", version=__version__)
    sub = app.add_subparsers(dest="command", required=True)
    for name in [
        "ingest",
        "overview",
        "expand",
        "search",
        "follow",
        "read",
        "query",
        "replay",
        "export",
        "manifest",
        "verify",
        "backup",
        "gc",
        "pin",
        "serve",
        "mcp",
        "schemas",
        "evaluate",
        "group",
        "enrich",
        "relate",
        "topics",
    ]:
        command = sub.add_parser(name)
        command.add_argument("--db", default=".navconr/index.sqlite")
        if name == "group":
            command.add_argument("title")
            command.add_argument("ids", nargs="+")
        if name == "relate":
            command.add_argument("--minimum", type=float, default=0.5)
        if name == "enrich":
            command.add_argument("--model", required=True)
            command.add_argument("--endpoint", default="http://127.0.0.1:11434")
            command.add_argument("--model-tokens", type=int, default=16000)
        if name == "ingest":
            command.add_argument("root")
            command.add_argument("--block-bytes", type=int, default=2048)
        if name in {"search", "query"}:
            command.add_argument("query")
            command.add_argument(
                "--mode", choices=["lexical", "vector", "hybrid", "semantic"], default="lexical"
            )
        if name in {"expand", "read"}:
            command.add_argument("ids", nargs="+")
        if name == "follow":
            command.add_argument("id")
            command.add_argument("--relation", default="reference")
        if name in {"overview", "expand", "follow", "search"}:
            command.add_argument("--limit", type=int, default=20)
            command.add_argument("--cursor")
        if name in {
            "overview",
            "expand",
            "follow",
            "search",
            "read",
            "query",
            "export",
            "manifest",
        }:
            command.add_argument("--revision")
        if name in {"query", "read"}:
            command.add_argument("--source-bytes", type=int, default=16000)
        if name == "read":
            command.add_argument("--range", nargs=2, type=int, metavar=("START", "END"))
        if name == "query":
            command.add_argument(
                "--policy", choices=["fixed", "adaptive", "model"], default="fixed"
            )
            command.add_argument("--model")
            command.add_argument("--endpoint", default="http://127.0.0.1:11434")
            command.add_argument("--steps", type=int, default=64)
            command.add_argument("--seconds", type=float, default=60)
        if name == "replay":
            command.add_argument("run_id")
        if name == "backup":
            command.add_argument("destination")
        if name == "pin":
            command.add_argument("revision")
        if name == "export":
            command.add_argument("--include-source", action="store_true")
        if name == "serve":
            command.add_argument("--port", type=int, default=8765)
            command.add_argument("--viewer", default=None)
        if name == "evaluate":
            command.add_argument("--reader-model")
            command.add_argument("--reader-endpoint", default="http://127.0.0.1:11434")
            command.add_argument("dataset")
            command.add_argument("--output", default="benchmarks/results")
            command.add_argument("--split", choices=["dev", "heldout"], default="dev")
            command.add_argument("--budgets", type=int, nargs="+", default=[512, 2048])
    return app


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "schemas":
            output(
                {
                    name: cls.model_json_schema()
                    for name, cls in vars(models).items()
                    if isinstance(cls, type) and issubclass(cls, models.Record)
                }
            )
            return 0
        with Index(args.db) as index:
            command = args.command
            if command == "topics":
                output({"revision": index.group_topics().revision})
            elif command == "group":
                output({"revision": index.group(args.title, args.ids).revision})
            elif command == "relate":
                from .relationships import suggest_related

                candidates = suggest_related(index, minimum=args.minimum)
                output(
                    {"revision": index.link(candidates).revision, "relationships": len(candidates)}
                )
            elif command == "enrich":
                from .budget import Budget
                from .enrichment import enrich

                output(
                    asyncio.run(
                        enrich(
                            index,
                            OllamaProvider(args.model, args.endpoint),
                            Budget(Limits(model_tokens=args.model_tokens, model_calls=10000)),
                        )
                    )
                )
            elif command == "ingest":
                try:
                    before = index.store.load()
                except NavconrError:
                    before = None
                after = index.ingest(args.root, block_bytes=args.block_bytes)
                output(
                    {
                        "revision": after.revision,
                        "sources": len(after.sources),
                        "nodes": len(after.nodes),
                        "spans": len(after.spans),
                        "diagnostics": after.diagnostics,
                        "changes": changes(before, after) if before else None,
                    }
                )
            elif command == "query":
                provider = OllamaProvider(args.model, args.endpoint) if args.model else None
                result = asyncio.run(
                    Navigator(
                        index, policy=args.policy, provider=provider, search_mode=args.mode
                    ).retrieve(
                        args.query,
                        revision=args.revision,
                        limits=Limits(
                            steps=args.steps, seconds=args.seconds, source_bytes=args.source_bytes
                        ),
                    )
                )
                output(result)
                return 1 if result.stop_reason == "failed" else 0
            elif command == "replay":
                output(index.store.run(args.run_id))
            elif command == "manifest":
                print(export_manifest(index.store.load(args.revision)))
            elif command == "export":
                data = index.store.load(args.revision)
                payload = data.model_dump()
                # Root filesystem paths are local metadata and omitted from shareable export.
                payload["root"] = "[local source root]"
                if not args.include_source:
                    payload["nodes"] = {
                        nid: {**node, "summary": ""} for nid, node in payload["nodes"].items()
                    }
                else:
                    payload["evidence"] = {
                        sid: index.session(args.revision, Limits(source_bytes=10_000_000))
                        .read([sid])[0]
                        .model_dump()
                        for sid in data.spans
                    }
                output(payload)
            elif command == "verify":
                output(index.store.verify())
            elif command == "backup":
                index.store.backup(args.destination)
                output({"backup": str(Path(args.destination).resolve())})
            elif command == "gc":
                output(index.store.gc())
            elif command == "pin":
                index.store.pin(args.revision)
                output({"pinned": args.revision})
            elif command == "serve":
                from .server import serve

                serve(
                    index,
                    args.port,
                    Path(args.viewer)
                    if args.viewer
                    else (
                        Path("viewer/dist")
                        if Path("viewer/dist").exists()
                        else Path(__file__).parent / "_viewer"
                    ),
                )
            elif command == "mcp":
                from .integrations import run_mcp

                run_mcp(index)
            elif command == "evaluate":
                from .evaluation import evaluate

                output(
                    asyncio.run(
                        evaluate(
                            index,
                            Path(args.dataset),
                            Path(args.output),
                            split=args.split,
                            budgets=args.budgets,
                            reader=OllamaProvider(args.reader_model, args.reader_endpoint)
                            if args.reader_model
                            else None,
                        )
                    )
                )
            else:
                session = index.session(
                    args.revision, Limits(source_bytes=getattr(args, "source_bytes", 16000))
                )
                kwargs = (
                    {"limit": args.limit, "cursor": args.cursor} if hasattr(args, "limit") else {}
                )
                if command == "overview":
                    output(session.overview(**kwargs))
                elif command == "expand":
                    output(session.expand(args.ids, **kwargs))
                elif command == "search":
                    output(session.search(args.query, mode=args.mode, **kwargs))
                elif command == "follow":
                    output(session.follow(args.id, relation=args.relation, **kwargs))
                elif command == "read":
                    ranges = {sid: tuple(args.range) for sid in args.ids} if args.range else None
                    output([item.model_dump() for item in session.read(args.ids, ranges=ranges)])
        return 0
    except (NavconrError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
