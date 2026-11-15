"""Prepare the authored example with a topic map and a recorded retrieval."""

import argparse
import asyncio
from pathlib import Path

from navconr import Index
from navconr.navigation import Navigator

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--db", default=".navconr/demo.sqlite")
args = parser.parse_args()
with Index(ROOT / args.db) as index:
    index.ingest(ROOT / "examples/corpus")
    members = [
        node.id
        for node in index.store.load().nodes.values()
        if node.kind == "section" and node.title in {"Refresh tokens", "Revocation"}
    ]
    index.group("Token lifecycle", members)
    result = asyncio.run(Navigator(index).retrieve("refresh token revocation"))
    print(
        f"Demo ready: revision {result.revision}, run {result.run_id}, {len(result.evidence)} original evidence spans."
    )
