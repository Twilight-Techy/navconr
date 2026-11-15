"""Bundle only authored fixtures, code and recorded evidence; never private context dumps."""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = set()
for directory in [
    "paper",
    "docs/research",
    "docs/design",
    "docs/decisions",
    "benchmarks/corpus",
    "examples/corpus",
]:
    files.update(path for path in (ROOT / directory).rglob("*") if path.is_file())
files.update((ROOT / "src/navconr").glob("*.py"))
files.update((ROOT / "scripts").glob("*.py"))
for name in [
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "LICENSE_STATUS.md",
    "benchmarks/dataset.json",
    "benchmarks/create_fixtures.py",
    "reports/scale.json",
    "reports/wheel-smoke.json",
]:
    files.add(ROOT / name)
for split in ["dev", "heldout"]:
    summary = ROOT / "reports" / f"smoke-{split}.json"
    report = json.loads(summary.read_text())
    directory = Path(report["path"]).resolve()
    if not directory.is_relative_to(ROOT / "benchmarks/results"):
        raise ValueError("result directory is outside the expected artifact root")
    files.add(summary)
    files.update(path for path in directory.iterdir() if path.is_file())
aliases = {}
reproduction = Path(
    json.loads((ROOT / "reports/wheel-smoke.json").read_text())["reproduction_path"]
).resolve()
if not reproduction.is_relative_to(ROOT / ".navconr/wheel-reproduction"):
    raise ValueError("unexpected reproduction artifact path")
for path in reproduction.iterdir():
    if path.is_file():
        files.add(path)
        aliases[path] = "reproduction/" + path.name
destination = ROOT / "dist" / "navconr-research-draft.zip"
destination.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, aliases.get(path, path.relative_to(ROOT)))
    archive.writestr(
        "BUNDLE_README.md",
        """# Preliminary research artifact

This archive contains authored fixtures, core source, recorded software experiments,
an isolated-wheel reproduction, and a preliminary manuscript. It is not a completed
scientific study or a public license grant. Private conversation dumps are excluded.

To rerun core experiments after extracting:

    uv sync --locked --extra dev --extra formats --extra search --extra mcp --extra langgraph --extra research
    .venv/bin/python benchmarks/create_fixtures.py
    .venv/bin/navconr ingest benchmarks/corpus --db .navconr/benchmark.sqlite
    .venv/bin/navconr evaluate benchmarks/dataset.json --db .navconr/benchmark.sqlite --split dev
    .venv/bin/navconr evaluate benchmarks/dataset.json --db .navconr/benchmark.sqlite --split heldout

Use the separate source distribution for the complete inspector and repository docs.
Absolute paths in recorded manifests describe the original run; reruns create new
manifests. Source/evidence metrics, not identical run IDs or latency, are the checked
reproduction targets. No live model invocation is required by these commands.
""",
    )
manifest = {
    "file": destination.name,
    "files": len(files) + 1,
    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    "status": "preliminary draft; no independent research validation or submission",
    "license": "unresolved",
    "private_context_included": False,
}
(ROOT / "reports" / "research-bundle.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest, indent=2))
