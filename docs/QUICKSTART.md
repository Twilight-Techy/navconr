# Run Navconr locally

From the repository root, run `make setup`. This creates `.venv`, installs the editable library and optional development/format/search/MCP dependencies, and installs locked viewer dependencies. Python 3.11+ and Node 22 are the declared targets; recorded verification is in `reports`.

```bash
.venv/bin/navconr ingest examples/corpus --db .navconr/demo.sqlite
.venv/bin/navconr overview --db .navconr/demo.sqlite
.venv/bin/navconr search 'refresh tokens' --db .navconr/demo.sqlite
.venv/bin/navconr query 'refresh token revocation' --db .navconr/demo.sqlite
```

Query returns original evidence, a pinned revision, usage, a stop reason, and the observed action trace. It does not claim to generate an answer. Use `--policy adaptive` for the experimental budget-dependent heuristic. The default fixed policy uses no LLM.

For a prepared example including a semantic topic map and a recorded run, execute `python scripts/prepare_demo.py`. To inspect the collection and recorded runs:

```bash
cd viewer
npm run build
cd ..
.venv/bin/navconr serve --db .navconr/demo.sqlite
```

The server prints its loopback URL, normally `http://127.0.0.1:8765`. Search, expand nodes, select evidence, follow explicit links, and open the trace tab. The inspector reads existing runs; create new runs through the library or CLI. It never launches a model itself. Stop with Ctrl-C.

For your own knowledge collection, replace `examples/corpus` with a directory you intend to index. Source discovery excludes hidden paths, environments, package caches, generated bundles, and runtime storage. Symlinks escaping the root are excluded. Existing snapshots preserve old evidence when sources change.

Optional model-directed navigation, when deliberately configured:

```bash
.venv/bin/navconr query 'your question' --db .navconr/demo.sqlite \
  --policy model --model your-installed-ollama-model \
  --endpoint http://127.0.0.1:11434
```

The selected endpoint receives query/map/evidence content. Navconr does not install models, start Ollama, or call a remote model by default. One minimal Claude API answer smoke test is recorded; broader model checks remain pending. See [API](API.md) for optional enrichment and answer synthesis.

Run the software smoke evaluation with `make benchmark`. Results include manifests and original per-question outcomes. They are authored fixtures, not independently reviewed research results. See [evaluation guidance](EVALUATION.md).
