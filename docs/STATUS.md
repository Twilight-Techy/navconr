# Current implementation and acceptance status

The local system is implemented as `0.1.0rc1`. It includes the library, CLI, format adapters, bounded navigation/read tools, semantic maps, optional model interfaces, inspector, agent integrations, experiment runner and build tooling. This is a local development candidate with remaining research and public-distribution gates.

| Area | Verified local behavior | Remaining gate |
| --- | --- | --- |
| Core/evidence | Immutable snapshots, revisions, exact source/artifact byte reads, validated references | Development schema 1→2 migration and rollback are tested; future migrations need separate checks |
| Ingestion | Markdown/text, PDF pages, Python/TypeScript, HTML, DOCX, notebook source cells | OCR, images and richer format fidelity are later extensions |
| Maps and retrieval | Bounded physical/topic views, explicit/import/inferred provenance, lexical/vector/hybrid search, fixed/adaptive navigation | Strong learned-embedding evaluation |
| Model interfaces | Mock-tested policy/enrichment; one Claude API cited-answer smoke passes | Broader live navigation, enrichment and research evaluation remain pending |
| Operations | Unchanged-source reuse, atomic publication, integrity checks, backup/restore, pins and GC | Measured scale limits remain workload-specific |
| Inspector | Search, source/topic maps, relationship-origin filters, exact evidence, trace replay, responsive layout | No hosted multi-user service is included |
| Agents | LangGraph/LangChain tools and reference workflow, real MCP stdio client/server | Live-model agent evaluation remains deferred |
| Evaluation | 70 authored questions, nine local methods, two budgets, both software partitions, raw manifests/results | Independent human review, representative research corpora, original upstream-system runs and final study |
| Distribution/paper | MIT-licensed public source, local build tooling, friendly/technical READMEs, manuscript draft and result figures | Package-registry identity, dependency/asset review, full release approval, research validation and authorized registry publication/submission |

Completed checks: the original 52 Python tests on each of Python 3.11, 3.12 and 3.13; the expanded 61-test suite locally after Claude adapter work; three browser workflows; static typing, lint/format checks; viewer build; 1,260 local software-fixture comparisons without runtime failures; 100–1,000 source scale fixtures with bounded map pages. See [validation evidence](../reports/validation.json), [scale data](../reports/scale.json), [development results](../reports/smoke-dev.json), and [second software partition](../reports/smoke-heldout.json).

The checkbox tracker records 51 verified deliverables and 14 open acceptance tasks. Independent implementation proceeded while the user explicitly deferred real-model checks. A checked deliverable does not waive a milestone's model, research, licensing or publication requirements. [TASKS.md](TASKS.md) retains the original acceptance criteria and current evidence for open items.

Run the authored demonstration with `.venv/bin/python scripts/prepare_demo.py`, build `viewer/`, then use `make viewer`. [QUICKSTART.md](QUICKSTART.md) describes setup and commands; [API.md](API.md) covers integration. The server is local-only and browser test servers stop after checks.

The [manuscript](../paper/manuscript.md) is explicitly preliminary. Its tables and figures come from recorded authored-fixture runs. The separate [Claude smoke receipt](../reports/anthropic-smoke.json) records one narrow live answer check. No independent research claim, live-model comparison, upstream reproduction, registry publication or paper submission is asserted.

The isolated wheel serves its bundled inspector without the format/MCP/framework extras and reproduces the development experiment metrics and evidence costs. A prior cross-revision FTS ranking issue was found by that check, corrected with database schema 2 and regression-tested; see [ADR 002](decisions/002-revision-local-search.md) and [wheel verification](../reports/wheel-smoke.json).

Public source repository: [Twilight-Techy/navconr](https://github.com/Twilight-Techy/navconr), under the [MIT license](../LICENSE). Source was published and public visibility verified on 2026-11-15. Private context history and runtime artifacts stay outside Git; registry releases, dependency/asset review and paper submission remain open.
