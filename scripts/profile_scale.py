"""Local scale measurements on fictional sources; no asymptotic claim."""

import argparse
import asyncio
import json
import resource
import tempfile
import time
from pathlib import Path

from navconr import Index, Limits
from navconr.navigation import Navigator


def measure(count):
    with tempfile.TemporaryDirectory(prefix="navconr-scale-") as directory:
        base = Path(directory)
        root = base / "corpus"
        root.mkdir()
        for i in range(count):
            (root / f"service-{i:05}.md").write_text(
                f"# Service {i}\n\n## Routing\n\nService identifier key{i:05} uses port {8000 + i}.\n"
            )
        with Index(base / "index.sqlite") as index:
            started = time.perf_counter()
            data = index.ingest(root)
            indexing = time.perf_counter() - started
            started = time.perf_counter()
            result = asyncio.run(
                Navigator(index).retrieve(
                    f"key{count - 1:05}", limits=Limits(source_bytes=512, steps=128)
                )
            )
            query_ms = (time.perf_counter() - started) * 1000
            session = index.session(limits=Limits(steps=1000, map_bytes=4_000_000))
            cursor = None
            cards, pages, largest_page = 0, 0, 0
            while True:
                page = session.overview(limit=20, cursor=cursor)
                cards += len(page.items)
                pages += 1
                largest_page = max(largest_page, len(page.model_dump_json().encode()))
                cursor = page.next_cursor
                if cursor is None:
                    break
            assert cards == count
            assert largest_page <= 16384
            assert any(f"key{count - 1:05}" in evidence.text for evidence in result.evidence)
            started = time.perf_counter()
            (root / "service-00000.md").write_text(
                "# Changed service\n\nChanged source evidence.\n"
            )
            index.ingest(root)
            update = time.perf_counter() - started
            return {
                "sources": count,
                "nodes": len(data.nodes),
                "index_seconds": indexing,
                "update_seconds": update,
                "query_ms": query_ms,
                "database_bytes": index.store.path.stat().st_size,
                "overview_pages": pages,
                "largest_map_page_bytes": largest_page,
                "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "rss_note": "Cumulative process high-water mark on Linux, not a per-index allocation measure",
                "stop_reason": result.stop_reason,
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 500, 1000])
    parser.add_argument("--output", default="reports/scale.json")
    args = parser.parse_args()
    rows = [measure(size) for size in args.sizes]
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {"schema_version": 1, "fixture": "generated fictional Markdown services", "rows": rows},
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(rows, indent=2))
