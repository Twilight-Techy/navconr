"""Requires navconr[langgraph]; runs without a model or credentials."""

import asyncio
from pathlib import Path

from navconr import Index
from navconr.langgraph_integration import retrieval_graph


async def main():
    root = Path(__file__).resolve().parents[1]
    with Index(root / ".navconr/langgraph-example.sqlite") as index:
        index.ingest(root / "examples/corpus")
        graph = retrieval_graph(index)
        state = await graph.ainvoke({"query": "refresh token revocation"})
        for evidence in state["retrieval"]["evidence"]:
            print(evidence["span"]["source"], evidence["text"])


if __name__ == "__main__":
    asyncio.run(main())
