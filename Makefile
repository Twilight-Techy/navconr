.PHONY: setup check demo viewer benchmark release
PYTHON := .venv/bin/python
NAVCONR := .venv/bin/navconr

setup:
	uv sync --locked --extra dev --extra formats --extra search --extra mcp --extra langgraph
	cd viewer && npm ci

check:
	.venv/bin/ruff check src tests scripts benchmarks/create_fixtures.py
	.venv/bin/ruff format --check src tests scripts benchmarks/create_fixtures.py
	.venv/bin/mypy src/navconr
	.venv/bin/pytest -q
	cd viewer && npm run build

demo:
	$(NAVCONR) ingest examples/corpus --db .navconr/demo.sqlite
	$(NAVCONR) query 'refresh token revocation' --db .navconr/demo.sqlite

viewer:
	$(NAVCONR) serve --db .navconr/demo.sqlite

benchmark:
	$(PYTHON) benchmarks/create_fixtures.py
	$(NAVCONR) ingest benchmarks/corpus --db .navconr/benchmark.sqlite
	$(NAVCONR) evaluate benchmarks/dataset.json --db .navconr/benchmark.sqlite --split dev

release:
	$(PYTHON) scripts/release.py
