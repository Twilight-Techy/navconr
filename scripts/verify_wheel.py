"""Run with an isolated wheel environment, never the editable development install."""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import HTTPServer
from pathlib import Path

import httpx

import navconr
from navconr import Index
from navconr.evaluation import evaluate
from navconr.navigation import Navigator
from navconr.server import make_handler

ROOT = Path(__file__).resolve().parents[1]
installed = Path(navconr.__file__).resolve()
assert installed.is_relative_to(Path(sys.prefix).resolve()), (
    "Run this with the isolated wheel interpreter."
)
assets = installed.parent / "_viewer"
assert (assets / "index.html").is_file(), "Bundled inspector is missing."

with tempfile.TemporaryDirectory(prefix="navconr-wheel-") as directory:
    base = Path(directory)
    shutil.copytree(ROOT / "examples/corpus", base / "corpus")
    with Index(base / "index.sqlite") as index:
        index.ingest(base / "corpus")
        result = asyncio.run(Navigator(index).retrieve("refresh token revocation"))
        assert result.evidence and result.stop_reason == "completed"
        assert any("Redis" in evidence.text for evidence in result.evidence)
        version = subprocess.check_output(
            [sys.executable, "-m", "navconr.cli", "--version"], cwd=base, text=True
        ).strip()
        assert version == "0.1.0rc1"
        server = HTTPServer(("127.0.0.1", 0), make_handler(index.store.path, assets))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            response = httpx.get(f"http://127.0.0.1:{server.server_port}/")
            assert response.status_code == 200 and "Navconr" in response.text
            assert (
                httpx.get(f"http://127.0.0.1:{server.server_port}/api/status").json()["sources"]
                == 3
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    shutil.copytree(ROOT / "benchmarks/corpus", base / "benchmark-corpus")
    output = ROOT / ".navconr/wheel-reproduction"
    output.mkdir(parents=True, exist_ok=True)
    with Index(output / "index.sqlite") as index:
        index.ingest(base / "benchmark-corpus")
        repeat = asyncio.run(
            evaluate(
                index,
                ROOT / "benchmarks/dataset.json",
                output / "results",
                split="dev",
                budgets=[512, 2048],
            )
        )
        baseline = json.loads((ROOT / "reports/smoke-dev.json").read_text())
        fields = [
            "method",
            "budget",
            "questions",
            "evidence_recall",
            "complete_evidence",
            "correct_abstention",
            "mean_evidence_bytes",
            "failures",
        ]
        actual = [{key: row[key] for key in fields} for row in repeat["summary"]]
        expected = [{key: row[key] for key in fields} for row in baseline["summary"]]
        assert actual == expected, "Independent installation changed retrieval/scoring metrics."

report = {
    "schema_version": 1,
    "version": version,
    "module": str(installed),
    "isolated_install": True,
    "bundled_inspector_http": True,
    "exact_retrieval": True,
    "core_without_format_mcp_framework_extras": True,
    "reproduction_rows": repeat["rows"],
    "retrieval_and_cost_metrics_match": True,
    "latency_comparison": "not asserted",
    "reproduction_path": repeat["path"],
    "research_gate": "software reproduction only; independent research study still pending",
}
(ROOT / "reports/wheel-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
