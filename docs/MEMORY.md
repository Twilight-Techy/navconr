# Project memory

Last updated: 2026-11-15 (Africa/Lagos).

## Purpose and user intent

Build a developer library that gives LLM agents a lightweight, navigable index of a knowledge collection. The agent progressively inspects more detailed maps and fetches exact original source spans when useful. Large indexes must themselves be navigable in bounded portions. The representation may use a tree, graph, DAG, or a combination.

The user wants a research paper, a usable library, and a visualization layer for inspecting structure, relationships, and retrieval paths. They have now requested an end-to-end implementation plan, project rules, task order, and a memory file in `docs`.

The user explicitly required the original dump extraction to preserve the source conversation, not summarize or rewrite it. Keep `context/conversation.md` and both dumps as historical source material.

## Historical source and findings

- `context/dump_1.json` and `context/dump_2.json` contain identical message lists. Differences are owner metadata and ordering of the same safe URLs.
- `context/conversation.md` contains the ten nonempty conversation messages once, in order: five user messages and five assistant messages. Export metadata, seven internal citation markers, and 24 code-fence export IDs were removed. Extracted messages were checked against both dumps.
- The original assistant suggested many technologies and made strong performance and novelty claims. Those statements are discussion context, not validated project results.

## Established direction

- The central user idea is progressive navigation over indexes with exact references into original knowledge sources.
- A single navigation entry may refer to multiple source locations.
- ReAct-style agents are an intended use case; integration should permit other agent policies.
- Navigation can include several levels and relationships across branches; a graph database is not a requirement.
- Extensible ingestion and retrieval are intended. Visualization and experimental evaluation are part of the broader project.
- The user requested planning after the implementation recommendations. Technical choices below are the working baseline and may be revised with evidence.

## Working technical baseline

| Area | Current direction | Status |
| --- | --- | --- |
| Project name | Navconr, from workspace name | Working label; package availability unverified |
| First use case | Collections of Markdown technical documentation | Planning baseline |
| Core | Python library with typed interfaces and Pydantic schemas | Planning baseline |
| Storage | SQLite, FTS5, immutable local source snapshots | Planning baseline |
| Parsing | `markdown-it-py` initially; adapters for additional formats | Planning baseline |
| Representation | Physical hierarchy plus separate semantic groups and typed edges | Planning baseline |
| Evidence | Versioned sources, exact spans, explicit extraction mappings | Required invariant |
| Navigation | Bounded tools plus a reference controller; batched expansion, recovery, and budgets | Planning baseline |
| Search | Lexical first; vector and hybrid options for recovery and evaluation | Planning baseline |
| Viewer | Separate React/React Flow inspector driven by exports and traces | Planning baseline |
| Integration | CLI, tool schemas, reference agent integration, optional MCP server | Planned after core stability |
| First release boundary | Milestones M0–M11 in the plan | Planning baseline |

## Research position

The broad concept is not established as novel. Related systems already cover important parts:

- [PageIndex](https://github.com/VectifyAI/PageIndex): reasoning-driven tree retrieval and a corpus navigation layer.
- [RAPTOR](https://arxiv.org/abs/2401.18059): recursively constructed summary trees.
- [LlamaIndex recursive retrieval](https://developers.llamaindex.ai/python/framework/integrations/retrievers/recursive_retriever_nodes/): traversal through node references.
- [GraphRAG DRIFT](https://microsoft.github.io/graphrag/query/drift_search/): iterative exploration using global and local graph context.
- [IRCoT](https://arxiv.org/abs/2212.10509): interleaved reasoning and retrieval.
- [NavTree preprint](https://arxiv.org/abs/2610.06902): navigation without LLM-generated summaries under matched-cost evaluation.

These sources were checked during the planning discussion; this is not an exhaustive literature review or an independent reproduction of their results.

Candidate research question: under fixed retrieval budgets, when does progressive navigation improve evidence coverage and answer quality compared with strong search baselines?

Candidate method: adaptive allocation of a retrieval budget across map inspection, branch exploration, and source reading. Neither novelty nor superiority has been demonstrated.

## Open decisions and when to resolve them

| Decision | Resolve by | Default path |
| --- | --- | --- |
| Python support range and package/module names | T007 | Choose supported stable tooling; verify name before publication |
| Exact schema, ID lifecycle, and locator contracts | T003–T004 | Versioned sources, stable logical identities where resolvable, immutable node revisions |
| Pilot corpus and evidence annotation rubric | T005 | Markdown technical documentation with manually reviewed evidence |
| LLM provider/model and tokenizer | T015/T025 | Configurable adapter; fake provider for CI; record chosen real models |
| Embedding model and local vector implementation | T031 | A reproducible local baseline selected for the evaluation corpus |
| Quantitative performance targets | T005/T035 | Correctness gates first; empirical quality/cost targets after pilot, before held-out evaluation |
| Cross-document semantic grouping policy | T016/T029 | Explicit hierarchy first; test generated grouping against deterministic grouping |
| PDF extraction and code-parser dependencies | T045–T047 | Evaluate source fidelity and locator quality before selecting adapters |
| Distribution license, public corpora, package identity | T060–T062 | Record choices and redistribution terms before publishing |
| Final paper claim and venue | T056–T059 | Follow measured findings and completed related-work review |
| Public publishing, hosting, and submission | T064–T065 | Prepare artifacts first; obtain applicable user authorization before execution |

## Current state

- User authorized building and running the entire project. The local implementation is version `0.1.0rc1`.
- Implemented: versioned SQLite source/artifact snapshots, exact UTF-8 byte evidence, physical hierarchies, bounded maps, explicit links/imports, separate semantic groups, provenance-filtered relationships, update reuse, integrity/backup/retention/GC.
- Supported adapters: Markdown/text, text-based PDF pages, Python AST, TypeScript/TSX tree-sitter, HTML, DOCX and notebook source cells. Format limitations are in ADAPTERS.md.
- Retrieval: FTS5 lexical, TF-IDF vectors, reciprocal-rank hybrid, optional sentence-transformer encoder, fixed/adaptive navigation, optional Ollama policy/enrichment/answering, budgets, source-pinned traces and replay.
- Interfaces: CLI, framework-neutral tools, real LangGraph/LangChain adapter and reference workflow, real MCP stdio transport, local React/React Flow inspector with physical/topic maps, relationship-origin filters, exact source panels and trace playback.
- Verification: 52 tests pass on each of Python 3.11, 3.12 and 3.13; three browser tests pass; Ruff and mypy checks pass. Viewer builds successfully. See reports for artifact and integration evidence.
- Authored data: 70 fictional questions, ten disjoint document families, two software-test partitions, nine methods and two budgets: 1,260 recorded local comparisons with no runtime failures. These are software checks, not a human-reviewed research pilot or answer-quality study.
- Scale checks cover 100, 500 and 1,000 sources. Host metadata remains whole-revision; updates rebuild metadata/FTS membership while reusing unchanged source parsing. Do not claim logarithmic resource growth.
- Paper: preliminary manuscript, actual-result figures and reproduction tooling. Scientific claims, independent study, upstream comparisons, author/venue and submission remain open.
- Public GitHub source repository: https://github.com/Twilight-Techy/navconr under Twilight-Techy. Source is pushed on main, which tracks origin/main. Package-registry publishing, distribution license and paper submission remain separate open items. Do not infer an open-source license.
- The user explicitly selected **Leave model checks pending**. Ollama is mock-tested; no live model checks or downloaded embedding-model runs have been performed. Do not ask again or run them without updated user direction.
- Context dumps and extracted original conversation remain unchanged and are excluded from release artifacts.
- TASKS.md owns checkbox status. A checked local deliverable does not close a deferred milestone gate.

## Next action

The local build is implemented and verified. Remaining acceptance work requires independently reviewed annotations, configured models/embeddings, compatible upstream runs, final study/protocol/claims, license/package-registry identity and authorized package publication/submission. Keep the user's real-model deferral in force. Do not replace scientific or external-release requirements with authored or mocked results.

Local artifacts and detailed evidence are under `dist/` and `reports/`; earlier exploratory experiment outputs were preserved under `.navconr/archive/experiments` rather than mixed with the final software checks.

## Reproduction and local run

- `make setup` installs the locked local development/format/search/MCP/LangGraph environment.
- `.venv/bin/python scripts/prepare_demo.py` prepares authored sample data, a topic map and a recorded retrieval.
- `make viewer` serves the local inspector; UI assets must be built first or supplied by the wheel.
- `make check` runs Python checks and builds the viewer. Browser tests prepare their own database.
- Software evaluation uses `benchmarks/create_fixtures.py` and `navconr evaluate`; manifests and raw rows identify code/environment/input revisions.
- Release preparation uses `scripts/release.py`; paper/figure/reproduction preparation uses scripts in `scripts/`. None publishes externally.

## Decision and handoff log

| Date | Event or decision | Reason / effect |
| --- | --- | --- |
| 2026-11-15 | Extracted duplicate dumps into one original-text Markdown conversation | Preserves source discussion without duplicated messages or export metadata |
| 2026-11-15 | Read complete extracted conversation and identified open implementation/research choices | Establishes project context |
| 2026-11-15 | Checked related work; treated novelty and performance as unproven | Closely overlapping systems exist |
| 2026-11-15 | Established end-to-end planning documents and ordered backlog | User requested plan, rules, tasks, and memory before implementation |

Future handoffs should add only durable information: changed decisions, completed milestones, relevant checks, unresolved failures, and the next ready task. Keep detailed task status in `TASKS.md`.

2026-11-15 implementation handoff: local code and software checks progressed through the planned milestones while explicitly retaining model/research/distribution gates. See STATUS.md and reports for current evidence.

Reproduction finding: the first isolated-wheel comparison caught evidence-cost differences caused by shared FTS statistics across retained revisions. Database schema 2 isolates FTS tables per revision and migrates schema 1 transactionally. Regression tests cover frozen ranking and migration/rollback. The rebuilt isolated wheel now reproduces all 630 development comparisons, including evidence costs; reports/wheel-smoke.json records that check. Record/tool JSON stays schema 1; database schema is 2.

Final local verification: source checkout and isolated wheel both retrieve exact evidence; bundled inspector serves from the wheel; repository ingestion, trace replay and backup/restore pass. Publication and the independent research study remain open.

2026-11-15 GitHub handoff: the user explicitly requested a public repository and source push. Target: https://github.com/Twilight-Techy/navconr. Preserve context/ and its local integrity receipt outside Git; omit environments, databases, build outputs and caches. Git commit identity uses the account’s GitHub noreply address. Source publication does not authorize a package-registry release or paper submission, and no distribution license was selected.

Verified GitHub publication: public repository https://github.com/Twilight-Techy/navconr created and initial source commit e86a550ab43f2f8720746486a6cd6d4ba4bfc8f9 pushed to main. GitHub visibility and matching remote/local commit were checked. Private context, local receipts, environments, databases, caches and build outputs are excluded. Registry release and paper submission remain pending; real-model deferral is unchanged.

GitHub CI portability correction: Python 3.11’s PackageMetadata typing protocol lacks get(), so the environment manifest now uses the required Name header through __getitem__. Mypy passes on Python 3.11/3.12/3.13, and all four evaluator tests pass on 3.11. Current hosted checks are available at https://github.com/Twilight-Techy/navconr/actions.
