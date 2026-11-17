# Project memory

Last updated: 2026-11-17 (Africa/Lagos).

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
- Navconr must embed in existing projects with application-owned model clients, credentials, agent loops, and request/response formats. Core protocols, caching and evaluation must not assume a vendor endpoint or SDK. Optional built-in adapters are conveniences, not the library boundary.
- User preference for future authorized paid smoke tests: use Haiku and keep requests/output/spend to the minimum. Do not default to Opus merely because an example names it. This preference does not itself authorize more paid calls.
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
| Public corpora, package identity, dependency/asset compatibility | T060–T062 | MIT selected; verify remaining redistribution terms and registry identity before package publication |
| Final paper claim and venue | T056–T059 | Follow measured findings and completed related-work review |
| Public publishing, hosting, and submission | T064–T065 | Prepare artifacts first; obtain applicable user authorization before execution |

## Current state

- User authorized building and running the entire project. The local implementation is version `0.1.0rc1`.
- Implemented: versioned SQLite source/artifact snapshots, exact UTF-8 byte evidence, physical hierarchies, bounded maps, explicit links/imports, separate semantic groups, provenance-filtered relationships, update reuse, integrity/backup/retention/GC.
- Supported adapters: Markdown/text, text-based PDF pages, Python AST, TypeScript/TSX tree-sitter, HTML, DOCX and notebook source cells. Format limitations are in ADAPTERS.md.
- Retrieval: FTS5 lexical, TF-IDF vectors, reciprocal-rank hybrid, optional sentence-transformer encoder, fixed/adaptive navigation, optional Ollama policy/enrichment/answering, budgets, source-pinned traces and replay.
- Interfaces: CLI, framework-neutral tools, real LangGraph/LangChain adapter and reference workflow, real MCP stdio transport, local React/React Flow inspector with physical/topic maps, relationship-origin filters, exact source panels and trace playback.
- Verification: the original 52-test suite passed on Python 3.11/3.12/3.13, followed by the 61-test Claude suite in hosted CI. The expanded provider-independent 74-test suite passes locally. Three browser tests previously passed; Ruff and mypy pass. Viewer builds successfully. Hosted checks cover the current suite on the supported matrix; see GitHub Actions for the current run.
- Embedding: root exports Index/Session/AgentTools/Navigator and neutral callable/protocol interfaces. An installed wheel was verified in a separate project with an application-specific callback, no vendor SDKs and no concrete HTTP-provider imports. CLI factories support query, enrichment and evaluation; protocol/identity consumers no longer require base_url. See docs/INTEGRATION.md and ADR 003.
- Authored data: 70 fictional questions, ten disjoint document families, two software-test partitions, nine methods and two budgets: 1,260 recorded local comparisons with no runtime failures. These are software checks, not a human-reviewed research pilot or answer-quality study.
- Scale checks cover 100, 500 and 1,000 sources. Host metadata remains whole-revision; updates rebuild metadata/FTS membership while reusing unchanged source parsing. Do not claim logarithmic resource growth.
- Paper: preliminary manuscript, actual-result figures and reproduction tooling. Scientific claims, independent study, upstream comparisons, author/venue and submission remain open.
- Public GitHub source repository: https://github.com/Twilight-Techy/navconr under Twilight-Techy. Source is pushed on main, which tracks origin/main. The user confirmed open-source distribution; MIT is selected, copyright 2026 Ibrahim Makanjuola (the owner's public GitHub profile name). Python/inspector metadata and future distribution scripts declare/include it. Package-registry identity/publishing, dependency/asset review, and paper submission remain open.
- The root README is the friendly introduction; README.technical.md covers architecture, APIs, budgets, integrations and development. Keep their commands executable and their claims consistent with STATUS.md.
- The user initially selected **Leave model checks pending**, then on 2026-11-17 supplied a Claude credential and explicitly authorized testing with absolute-minimum credit use. One Claude Opus 5.5 answer smoke passes: 377 input + 63 output tokens, estimated $0.002768; one generation, zero retries. The key was entered through a hidden terminal prompt and was never saved in files or reports. Do not repeat the paid run or start a broader paid study without new user direction. Ollama/live model-directed navigation and embedding-model downloads remain unrun.
- Context dumps and extracted original conversation remain unchanged and are excluded from release artifacts.
- TASKS.md owns checkbox status. A checked local deliverable does not close a deferred milestone gate.

## Next action

The local build is implemented and verified. Remaining acceptance work requires independently reviewed annotations, configured models/embeddings, compatible upstream runs, final study/protocol/claims, package-registry identity, dependency/asset review, and authorized package publication/submission. The user's minimal-cost authorization was exercised with one smoke request; keep broader paid validation pending and do not repeat the paid check automatically. Do not replace scientific or external-release requirements with authored or mocked results.

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

2026-11-15 GitHub handoff: the user explicitly requested a public repository and source push. Target: https://github.com/Twilight-Techy/navconr. Preserve context/ and its local integrity receipt outside Git; omit environments, databases, build outputs and caches. Git commit identity uses the account’s GitHub noreply address. Source publication does not authorize a package-registry release or paper submission. At this historical step no license was selected; the subsequent documentation request established MIT licensing.

Verified GitHub publication: public repository https://github.com/Twilight-Techy/navconr created and initial source commit e86a550ab43f2f8720746486a6cd6d4ba4bfc8f9 pushed to main. GitHub visibility and matching remote/local commit were checked. Private context, local receipts, environments, databases, caches and build outputs are excluded. Registry release and paper submission remain pending; real-model deferral is unchanged.

GitHub CI portability correction: Python 3.11’s PackageMetadata typing protocol lacks get(), so the environment manifest now uses the required Name header through __getitem__. Mypy passes on Python 3.11/3.12/3.13, and all four evaluator tests pass on 3.11. Current hosted checks are available at https://github.com/Twilight-Techy/navconr/actions.

2026-11-15 documentation/licensing update: the user requested a friendly main README, technical README and open-source license. Added README.technical.md and the standard MIT license, updated Python/inspector metadata and future release/research bundle generators, and reconciled current licensing statements. Hatchling's minimum is 1.27 for PEP 639 metadata; lockfiles retain existing dependency versions. Historical artifact receipts remain unchanged and describe their original builds. T060 stays open for registry identity and dependency/asset review.

Documentation verification: fresh locked core-only environment executes ingestion/query, both technical Python examples, demo preparation, integrity and backup commands. The inspector builds and serves the prepared demo. All 56 local links/images checked in the refreshed entry/contribution/release documents resolve; MCP JSON parses. New wheel/source builds include the exact MIT text; wheel metadata declares License-Expression MIT and License-File LICENSE, and the source archive includes both READMEs without private context. Changed Python scripts pass Ruff lint/format checks; uv lock --check and git diff --check pass. These checks make no live-model calls and do not replace independent research gates.

2026-11-17 README visual refresh: the user requested a more visually appealing main README. Added an original SVG banner in docs/assets/readme-hero.svg using the inspector's forest-green palette, centered navigation and CI/Python/MIT/status badges, a styled Mermaid workflow, compact feature/format/documentation tables, a linked inspector screenshot, and collapsible inspector setup. Python/CLI commands and the project's early-release/research limitations are retained. The technical README remains the developer reference.

Visual verification: reviewed local GitHub-style previews at desktop (1280px) and phone (390px) widths. All images/badges load, inspector details expand, Mermaid renders, and neither preview has page-wide horizontal overflow. SVG XML parses; all 20 local links/images/anchors resolve. The source distribution includes the banner and excludes private context; git diff --check passes. This presentation change needs no new runtime tests or live-model checks.

2026-11-17 minimum-cost Claude check: added AnthropicProvider and a StructuredProvider protocol for optional model components. The adapter uses the official HTTPS Messages endpoint/API version 2026-10-21, free preflight token counting, low effort, standard service, small input/output caps, no automatic retries/redirects, shared reservations and measured usage. T025's offline-integration plus explicit live-smoke acceptance is now met. Broader navigation/enrichment/model comparisons remain unverified.

One paid generation ran against one 120-byte fictional operations.md passage. The answer was "Delete the session's Redis session key." Exact source bytes and cited span membership pass. Measured 377 input + 63 output = 440 tokens; estimated cost $0.002768 at $4/$20 per million input/output tokens. No cached tokens, retries, model downloads or further paid calls. Receipt: reports/anthropic-smoke.json. scripts/smoke_anthropic.py can reproduce the narrow test only when explicitly invoked with credentials; do not rerun it routinely. New offline tests cover caps, refusal before generation, quota exhaustion, HTTP failures/redirects without retries or secret-bearing errors, malformed/truncated output, accounting and cancellation. Local full suite: 61 tests pass, Ruff and mypy pass. Never store the supplied credential in docs, source, environment files or reports.

2026-11-17 provider-independence correction: user clarified that Haiku should have been used for the cheap smoke and that Navconr must plug into any existing project without adopting a provider/request format. Persisted the cost preference in RULES.md and memory; future smoke commands default to claude-haiku-5-5 and use separate model-specific receipt paths. Historical Opus evidence remains unchanged. No new paid calls or credential use occurred.

Extracted HTTP-free model contracts into model.py; added CallableProvider, ModelRequest and ModelResponse; removed base_url requirements from enrichment/evaluation and introduced opaque configuration identities with a new enrichment cache namespace. Existing protocol imports stay compatible. Exposed embedding primitives from the root package, added CLI project factories, and supplied application-owned OpenAI/Anthropic SDK mappings plus an integration guide. Removed the built-in Claude adapter's smoke-specific 12-word instruction; brevity now belongs to the smoke task. ADR 003 records the ownership boundary and capability limits.

Verification: 74 local tests pass, including callback navigation/replay, SDK-shaped request/response variants, URL-free enrichment/evaluation, cache isolation, input/output accounting, failures/cancellation/deadlines and all three CLI factory paths. make check passes (Ruff, mypy, pytest and viewer build). A clean core wheel runs in a temporary separate project using application-specific response fields, with neither OpenAI nor Anthropic SDK installed and neither built-in HTTP adapter imported. Documentation links resolve. All model behavior in these new checks is offline fixture behavior, not live provider validation.
