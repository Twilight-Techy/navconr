# Ordered implementation tasks

Established: 2026-11-15. Local implementation and verification are complete for the checked tasks. Research, live-model, and public-distribution gates remain open; see current-evidence notes and STATUS.md. This backlog covers the complete first-release project, including research and publication preparation.

Read [RULES.md](RULES.md), [MEMORY.md](MEMORY.md), and the relevant milestone in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) before execution.

## How to execute

- Execute in numeric order by default; use the dependencies below to determine readiness.
- Work on one coherent task at a time. Independent work may overlap when useful, without changing the milestone gates.
- An unchecked task is open. Mark active work in the execution notes. Use `[x]` only after the acceptance checks pass and evidence is recorded.
- Record checks and artifact paths briefly under the completed task. Keep durable decisions and handoff context in `MEMORY.md`.
- If a task is blocked, record the actual dependency and continue useful independent work. Do not count permission or elapsed time as completion.
- T064 and T065 include external publication and require applicable user authorization. Preparing their concrete artifacts is earlier work and does not need publication approval.

## Milestone order and gates

| Milestone | Tasks | Depends on | Exit gate |
| --- | --- | --- | --- |
| M0: contracts and study design | T001–T006 | None | Explicit schemas, scope, and evaluation protocol |
| M1: minimal core | T007–T011 | M0 | Installable package, exact storage, versioned records |
| M2: Markdown ingestion | T012–T017 | M1 | Repeatable, source-grounded, bounded collection maps |
| M3: navigation tools | T018–T023 | M2 | Public tools find and return original evidence |
| M4: reference controller | T024–T029 | M3 | Recoverable, budgeted Markdown retrieval with traces |
| M5: pilot evaluation | T030–T035 | M4 | Reproducible quality/cost report and policy decisions |
| M6: inspector | T036–T039 | M5 | Structure/evidence inspection and trace playback |
| M7: maintenance and scale | T040–T044 | M6 | Safe updates, restore/migrations, measured scale |
| M8: formats and richer retrieval | T045–T051 | M7 | Tested adapters and compatible hierarchical comparisons |
| M9: integrations | T052–T055 | M8 | Stable API/CLI, agent integration, optional MCP adapter |
| M10: full study and paper | T056–T059 | M9 | Auditable results and independently checked manuscript |
| M11: release and handoff | T060–T065 | M10 | Verified release artifacts and authorized publication outcomes |

Task dependencies name direct prerequisites. Milestone gates also apply: an individual task being ready does not waive an earlier milestone's exit checks. Related-work reading and research notes continue throughout the project.

## M0 — Contracts and study design

- [x] **T001 — Write the product and scope brief.** Dependencies: none. Define target users, representative documentation questions, supported first-release workflows, scope boundaries, failure behavior, and terminology. Done when `docs/design/product.md` distinguishes prototype, full release, and later extensions with concrete examples.

- [x] **T002 — Build the related-work comparison matrix.** Dependencies: T001. Review PageIndex, RAPTOR, recursive reference retrieval, GraphRAG/DRIFT, IRCoT, NavTree, and any closer methods found during review. Done when `docs/research/related-work.md` cites primary sources, separates mechanisms from reported results, and identifies overlaps, uncertainties, and reproducible comparison candidates.

- [x] **T003 — Specify data and tool contracts.** Dependencies: T001. Define sources, artifacts, spans, nodes, relationships, revisions, budgets, events, results, errors, tool inputs, and bounded responses. Done when `docs/design/contracts.md` contains valid and invalid examples, pagination/batching behavior, and schema/versioning rules.

- [x] **T004 — Specify coordinates, identity, and revision semantics.** Dependencies: T003. Define original-byte vs extracted-text coordinates, line/page displays, disjoint spans, logical vs revision IDs, and stale reference behavior. Done when `docs/design/locators.md` resolves Unicode, CRLF, repeated text, binary extraction, edits, and renames without ambiguous evidence.

- [x] **T005 — Define the evaluation protocol.** Dependencies: T001, T002, T004. Specify question classes, gold evidence, alternate evidence sets, development/held-out splits, baselines, budget accounting, metrics, pilot size, and target-setting procedure. Done when `docs/research/evaluation-protocol.md` can guide annotation and experiments without consulting answer outputs during tuning.

- [x] **T006 — Record architecture and package decisions.** Dependencies: T003, T004, T005. Establish component boundaries, async policy, storage model, artifact layout, optional extras, and initial CLI scope. Done when architecture decisions in `docs/decisions/` explain choices and deferred decisions, with an implementation layout consistent with the plan.

## M1 — Minimal core

- [x] **T007 — Scaffold the package and development checks.** Dependencies: T006. Choose supported Python versions, module/build configuration, dependencies, lint/type/test tools, fixture layout, and CI. Done when a clean local installation and ordinary offline checks pass, with optional network/paid checks explicitly separated.

- [x] **T008 — Implement versioned domain schemas.** Dependencies: T003, T004, T007. Implement validated records, typed IDs/locators, errors, and serialization. Done when contracts round-trip, invalid references/ranges/types fail clearly, and exported schemas carry versions.

- [x] **T009 — Implement the SQLite store.** Dependencies: T008. Create tables, relational constraints, index revision publication, transactions, and reopen behavior. Done when committed revisions are consistent, failed writes roll back, and records survive reopening with foreign references validated.

- [x] **T010 — Implement immutable snapshots and exact reads.** Dependencies: T004, T009. Store original bytes and extraction artifacts by revision and resolve spans. Done when UTF-8, multibyte characters, CRLF/LF, duplicate text, empty sources, and invalid locators return exact bytes or explicit errors without rewriting evidence.

- [x] **T011 — Implement trace events and usage records.** Dependencies: T008, T009. Add ordered events, run identities, usage categories, cost metadata, safe serialization, and fake clocks/providers. Done when events round-trip and distinguish measured, estimated, missing, and reserved usage without exposing secrets.

## M2 — Markdown ingestion

- [x] **T012 — Implement the Markdown structure adapter.** Dependencies: T010. Parse headings, paragraphs, lists, tables, fences, and source links with original-position mappings. Done when fixture blocks map back to original text, malformed input has defined behavior, and heading nesting is preserved.

- [x] **T013 — Implement structural segmentation.** Dependencies: T012. Split oversized sections while preserving meaningful blocks, disjoint references, coverage, and ordering. Done when all content is accounted for, code/table boundaries are handled explicitly, and oversized indivisible blocks have a documented bounded-read strategy.

- [x] **T014 — Resolve explicit document relationships.** Dependencies: T013, T009. Resolve local links, fragments, adjacency, and physical containment. Done when cross-file links point to existing targets, external/unresolved links remain distinguishable, and root escape/symlink cases follow the configured source boundary.

- [x] **T015 — Add pluggable bounded enrichment.** Dependencies: T013, T011. Define an enrichment protocol, fake implementation, validation, cache keys, summary size bounds, and a no-model path. Done when invalid generated targets are rejected and unchanged content/configuration reuses enrichment. A production provider is added in T025.

- [x] **T016 — Build bounded collection and section maps.** Dependencies: T014, T015. Build the physical hierarchy plus separate collection navigation groups, node cards, and bounded fan-out. Done when thousands of sibling entries can be navigated in bounded pages/layers and no map requires duplicating source text.

- [x] **T017 — Assemble ingestion and its initial CLI.** Dependencies: T016. Add manifests, exclusions, source discovery, diagnostics, revision staging/publication, and an ingest command. Done when repeat ingestion is idempotent and failed parsing/enrichment leaves the last published index usable. Exclude generated index/runtime directories from recursive source discovery.

## M3 — Navigation tools

- [x] **T018 — Implement overview and expansion.** Dependencies: T017. Add public bounded map operations, batching, deterministic ordering, and revision-pinned cursors. Done when output budgets hold for large maps and stale/invalid cursors produce clear outcomes.

- [x] **T019 — Implement lexical search.** Dependencies: T017. Build FTS5 search over source-derived text and navigation entries with explicit scope and ranking metadata. Done when results expose revisioned candidates, pagination is stable, and exact identifiers/rare terms can be found outside the current branch.

- [x] **T020 — Implement relationship following.** Dependencies: T018, T014. Add typed edge filters, provenance, inverse queries where defined, and bounded traversal. Done when cross-document navigation resolves valid targets and missing/deleted/unresolved references remain explicit.

- [x] **T021 — Implement public evidence reads.** Dependencies: T018, T010. Add batched span reads, bounded range selection, display locators, and explicit partial outcomes. Done when public reads match original evidence byte-for-byte and oversized requests never silently truncate or regenerate text.

- [x] **T022 — Validate public tool contracts.** Dependencies: T018, T019, T020, T021. Finish request/response schemas, structured errors, revision compatibility, batching, and cancellation hooks. Done when contract tests cover all operations, invalid input, source-root boundaries, and declared response limits.

- [x] **T023 — Ship the manual-navigation vertical slice.** Dependencies: T022. Create a runnable example that inspects an overview, explores branches, follows a cross-document reference, and reads evidence. Done when a fresh local index supports the workflow entirely through public tools without an LLM or private APIs.

## M4 — Budgeted reference controller

- [x] **T024 — Implement shared budget enforcement.** Dependencies: T011, T022. Add reservations, token estimation/capability checks, reconciliation, deadlines, bounded concurrency, retries, and structured exhaustion reasons. Done when fake-provider tests cannot bypass limits through batching, retries, repeated prompts, parallel reservations, or direct tool use.

- [x] **T025 — Add a cancellable production model adapter.** Dependencies: T015, T024. Select a first real provider/model configuration and implement structured action/enrichment requests, tokenizer handling, output caps, timeout propagation, and usage reporting. Done when fake integration checks pass and an explicit opt-in real-provider smoke run is recorded without keys or private source leakage. Document unsupported hard guarantees.

  Current evidence: Ollama plus the opt-in Claude Messages adapter; nine additional offline transport/budget/schema/cancellation checks pass. An explicit one-generation Claude Opus 5.5 answer smoke passes with exact-byte/citation checks and measured usage, without credentials/private corpora in the receipt. See reports/anthropic-smoke.json. Broader live navigation/enrichment and research evaluation remain pending.

  Provider independence follow-up: HTTP-free protocols/callable adapter, application-owned clients/wire formats, opaque cache identities, root embedding exports, and CLI query/enrichment/evaluation factories are implemented and tested. A core wheel embeds in an independent project without model SDKs or concrete HTTP-provider imports. Haiku is the default for future authorized paid smoke tests; this correction used no paid calls.

- [x] **T026 — Implement a fixed navigation policy.** Dependencies: T025, T023. Add overview inspection, bounded frontier selection, expansion/search/read actions, evidence accumulation, cycle prevention, and explicit stops. Done when deterministic fixtures complete multi-step retrieval under a pinned index revision and return evidence, trace, usage, and stop reason.

- [x] **T027 — Implement recovery and incomplete-evidence behavior.** Dependencies: T026. Add multi-branch exploration, backtracking, global search, duplicate-span merging, and missing/contradictory evidence handling. Done when a misleading summary does not trap the controller and unanswerable fixtures terminate without invented evidence.

- [x] **T028 — Export and replay complete retrieval traces.** Dependencies: T027, T011. Capture all tool/model events, revisions, evidence references, errors, and accounting in a replayable format. Done when a saved run can be inspected without repeating model calls and incompatible/missing source artifacts have explicit outcomes.

- [x] **T029 — Add switchable summary and semantic-routing strategies.** Dependencies: T028, T016. Implement bounded summary-aware routing and optional cross-document topic grouping with a deterministic alternative. Done when strategies share the same contracts/budgets and can be enabled independently for ablations. Preserve the fixed policy as a baseline.

## M5 — Pilot evaluation

- [ ] **T030 — Assemble and annotate the pilot corpus.** Dependencies: T005, T029. Create development and held-out manifests, manually reviewed questions, required/alternate evidence sets, and answerability labels. Done when every scored question has an auditable annotation, document-family separation is checked, and annotation disagreements are recorded.

  Current evidence: 70 authored fixtures exist; independent human review of a research pilot remains pending.

- [ ] **T031 — Implement competent baseline retrievers.** Dependencies: T030, T019. Add a reproducible vector baseline, hybrid lexical/vector retrieval, parent–child retrieval, and structural-tree retrieval. Done when every baseline uses declared comparable source representations and budgets, with selected models/parameters/versioned configurations recorded.

  Current evidence: Local lexical/TF-IDF/hybrid/parent-child/tree baselines run; strong learned semantic baseline evaluation remains pending.

- [x] **T032 — Implement the experiment runner.** Dependencies: T031, T028. Run retrieval-only and optional shared-reader answer experiments, recording configurations, seeds/repeats, hashes, cache state, latency, and complete usage. Done when interrupted runs resume safely without mixing methods or dataset revisions.

- [x] **T033 — Implement evidence and answer scoring.** Dependencies: T032. Score evidence coverage, alternate sets, redundancy, citation support, answer correctness, and abstentions using the predefined rubric. Done when known scoring fixtures pass and ambiguous synthesis can be reviewed without relying solely on an unchecked model judge.

- [ ] **T034 — Run pilot comparisons and ablations.** Dependencies: T033. Compare summaries, edges, navigation, fixed/adaptive strategy variants, and several budgets. Done when runs include failures and full indexing/query costs, with a reproducible error taxonomy and no held-out tuning.

  Current evidence: 1,260 authored software-smoke comparisons run; the reviewed scientific pilot and model-dependent ablations remain pending.

- [ ] **T035 — Report findings and fix the next performance targets.** Dependencies: T034. Publish an internal pilot report and architecture decisions on retained strategies, quantitative quality/cost targets, and needed revisions. Done when results reproduce within recorded tolerances and targets are frozen before held-out evaluation. If major changes are needed, add explicit tasks instead of marking failed gates complete.

  Current evidence: Smoke reports exist; research quality/cost targets await the reviewed pilot.

## M6 — Inspector and visualization

- [x] **T036 — Define inspector exports and a local read bridge.** Dependencies: T035, T028. Export bounded nodes/relationships, source references, and trace events; add read-only local access and redaction modes. Done when schema versions, root restrictions, pagination, and source-free sharing are validated.

- [x] **T037 — Build expandable structure navigation.** Dependencies: T036. Scaffold the separate React viewer and implement tree/graph views, lazy loading, search, and physical/semantic relationship filters. Done when large maps can be explored without loading/rendering every node.

- [x] **T038 — Add source inspection and trace playback.** Dependencies: T037. Display exact evidence, selected paths, dead ends, action sequence, and cumulative usage. Done when a recorded retrieval can be replayed and inspected without generating new explanations or model calls.

- [x] **T039 — Verify the inspector workflow.** Dependencies: T038. Check keyboard interaction, empty/error/version states, large-map behavior, and a realistic wrong-branch investigation. Done when a developer can identify why evidence was missed and navigate to the original source locator using the viewer.

## M7 — Maintenance, operations, and scale

- [x] **T040 — Detect and stage source changes.** Dependencies: T039, T017. Handle additions, edits, deletions, and explicit/detected renames with revision manifests and changed-region tracking. Done when unchanged content is reused and ambiguous identity matches never silently rewrite old citations.

- [x] **T041 — Implement incremental index publication.** Dependencies: T040. Invalidate affected summaries/maps/edges/search entries and atomically publish a consistent revision. Done when readers pinned to an old revision remain consistent, current queries omit deleted sources, and interruption tests preserve a usable index.

- [x] **T042 — Implement migrations, retention, backup, and restore.** Dependencies: T041. Add version upgrade paths, retained-revision/pin rules, garbage collection, and recovery procedures. Done when migration/restore tests pass and garbage collection cannot remove evidence referenced by retained/pinned runs.

- [x] **T043 — Harden operational failure handling.** Dependencies: T042. Add bounded ingestion workers, provider throttling/retry handling, resumable stages, corrupt-artifact diagnostics, and storage concurrency documentation. Done when controlled failures recover predictably and no partial revision becomes visible.

- [x] **T044 — Profile corpus growth and set operational limits.** Dependencies: T043. Measure indexing time/memory, storage growth, update costs, map fan-out, query overhead, and viewer loading across increasing corpora. Done when a scale report states measured limits and bottlenecks without assuming logarithmic complexity.

## M8 — Additional formats and retrieval choices

- [x] **T045 — Add text-based PDF ingestion.** Dependencies: T044, T004. Select an extractor and implement pages, text artifacts, structural cues, and original-page mappings. Done when multi-page evidence resolves correctly, extraction limitations are documented, and image-only/OCR-required input is detected rather than advertised as supported.

- [x] **T046 — Add syntax-aware code ingestion.** Dependencies: T045, T014. Start with Python and TypeScript using suitable syntax parsers, then expose file/symbol structure and supported import references. Done when symbols map to exact source ranges, malformed/unsupported syntax has a fallback, and edge types distinguish syntax-derived references from resolved dependencies.

- [x] **T047 — Add HTML, DOCX, and notebook adapters in that order.** Dependencies: T046. Preserve source/artifact identity, headings/blocks, links, and notebook cell references with format-specific mappings. Done when all three adapters have fidelity fixtures, examples, explicit embedded-content policies, and documented unsupported features. Track each adapter's completion in execution notes.

- [x] **T048 — Add optional inferred relationship enrichment.** Dependencies: T047, T015. Implement candidate generation, target validation, provenance, deduplication, and optional similarity/model-inferred edges. Done when inferred links can be filtered/disabled, false-link fixtures are covered, and their effect can be evaluated independently.

- [x] **T049 — Stabilize optional vector and hybrid search adapters.** Dependencies: T048, T031. Turn validated baseline components into pluggable search implementations with persistence, updates, scope filters, and usage reporting. Done when adapter contract tests and incremental update checks pass without making embeddings mandatory for core use.

- [x] **T050 — Validate mixed-format collections.** Dependencies: T049. Exercise cross-format references, evidence reads, collection maps, updates, and visualization. Done when a realistic mixed collection retains exact source/artifact provenance and all adapter error cases remain visible through public tools.

- [ ] **T051 — Implement compatible hierarchical comparisons.** Dependencies: T050, T002, T032. Add runnable comparisons against the closest feasible PageIndex/RAPTOR/NavTree-style methods selected by the review. Done when original implementations vs reimplementations are identified and input conversions, supported tasks, budgets, and model differences are disclosed. Record exclusions with reasons rather than manufacturing parity.

  Current evidence: Exact-span external prediction importer implemented and tested; original upstream method executions remain not run.

## M9 — Integrations and stable interfaces

- [x] **T052 — Stabilize the public Python API and CLI.** Dependencies: T051. Review naming, async/sync boundaries, index lifecycle, configuration, errors, commands, and compatibility policy. Done when versioned API/CLI contract checks and fresh-user examples pass using built package artifacts.

- [x] **T053 — Publish tool schemas and one reference agent integration locally.** Dependencies: T052. Expose bounded tools and shared-budget sessions through a thin adapter to a selected agent framework. Done when the agent can navigate/read evidence, handle exhaustion, and cancel through public interfaces. This task prepares files; it does not require public publication.

- [x] **T054 — Implement the optional MCP adapter.** Dependencies: T053. Map tools to MCP with explicit roots, validated inputs, versioned outputs, and clear resource lifetimes. Done when local client integration checks cover normal navigation, malicious paths, unsupported revisions, deadlines, and cancellation without arbitrary filesystem/command access.

- [x] **T055 — Write and validate integration tutorials.** Dependencies: T054. Document library-only, CLI, own-agent, reference-agent, MCP, and inspector workflows plus provider/data-handling configuration. Done when a clean environment can execute each supported example and optional extras remain optional.

## M10 — Full research study and paper

- [ ] **T056 — Freeze the research claim and final protocol.** Dependencies: T055, T035, T051. Update related work, choose the precise contribution, set sample sizes/repeats from pilot evidence, and record held-out metrics/configurations. Done when the claim is testable and all exclusions, comparison budgets, and analysis rules are committed before the final runs.

  Current evidence: Protocol and candidate question documented; final research claim and held-out study protocol are not frozen.

- [ ] **T057 — Run held-out comparisons and sensitivity studies.** Dependencies: T056. Execute final baselines, fixed/adaptive policies, ablations, multiple budgets, and selected model/corpus sensitivity checks. Done when manifests, failures, costs, uncertainty estimates, and result tables are complete and no held-out tuning is hidden.

  Current evidence: Both software fixture partitions ran; a human-reviewed held-out research study has not run.

- [ ] **T058 — Write the paper and reproduction bundle.** Dependencies: T057. Produce methods, related work, results, limitations, figures, corpus/annotation documentation, and scripts. Done when every quantitative claim links to an experiment artifact and shareable data/assets have documented redistribution terms.

  Current evidence: Manuscript draft and plotting/reproduction scripts exist; final study and paper claims remain pending.

- [ ] **T059 — Perform an independent reproduction pass.** Dependencies: T058. Rebuild in a clean environment, rerun feasible checks, audit metric/claim alignment, and review limitations. Done when discrepancies are resolved or clearly reported and the manuscript is submission-ready. Independence means a fresh environment/review process; delegation is not required or implicitly authorized.

  Current evidence: Fresh-runtime software verification is separate from independent reproduction of the pending research study.

## M11 — Release, publication, and handoff

- [ ] **T060 — Resolve distribution identity and licensing.** Dependencies: T059. Verify package/repository names, choose the distribution license, audit dependency/asset compatibility, and identify any private material excluded from release. Done when release metadata and publishable-content boundaries are recorded; unresolved user-owned choices are surfaced before publication.

  Current evidence: Dependency inventory prepared; GitHub source target is Twilight-Techy/navconr. The user confirmed open-source distribution; MIT is selected in LICENSE, Python/inspector metadata and future artifact scripts. Package-registry identity and dependency/asset compatibility review remain open.

- [ ] **T061 — Complete release quality and boundary checks.** Dependencies: T060. Run relevant checks across supported environments, source-root/prompt-injection cases, migrations, backup/restore, provider capability behavior, and optional extras. Done when critical failures are fixed and material limitations appear in release notes.

  Current evidence: Local quality/boundary checks pass; full release gate retains deferred model checks and distribution review.

- [x] **T062 — Finish public-facing documentation and examples.** Dependencies: T061. Add quickstart, concepts, API reference, adapter matrix, deployment/use limits, evaluation report, contribution guide, maintenance/version policy, and changelog. Done when links/examples work, source permissions are respected, and documentation describes observed behavior.

- [ ] **T063 — Build and verify the release candidate.** Dependencies: T062. Produce wheel/source distribution and separately packaged viewer/integration artifacts as appropriate; inspect contents and install them cleanly. Done when a candidate version, artifact hashes, smoke-test evidence, paper bundle, and publication instructions are ready for review.

  Current evidence: Wheel/source candidates are built; the isolated installed wheel serves the bundled inspector and reproduces 630 development comparisons including evidence costs. Full release/research gates remain open.

- [ ] **T064 — Publish the authorized library release and verify it.** Dependencies: T063 and applicable user authorization. Publish approved artifacts and release notes to the chosen destinations. Done when the published version installs, examples work from published artifacts, and release references are recorded in memory. If authorization is absent, keep the candidate ready and this task open.

  Current evidence: Public GitHub source is published at https://github.com/Twilight-Techy/navconr on main. No package-registry release performed.

- [ ] **T065 — Submit the authorized paper and complete the handoff.** Dependencies: T059, T063 and applicable user authorization. Submit the approved manuscript/artifacts to the selected destination, verify references and access, and record outcomes. Done when submission/publication status, released versions, reproduction instructions, known limitations, and the next maintenance backlog are accurate. Library publication and paper submission can occur independently once their prerequisites are met.

  Current evidence: No paper submission performed.

## Execution notes

2026-11-15: Implemented the local library, format adapters, exact evidence tools, fixed/adaptive/model controllers, enrichment and answering interfaces, semantic groups/relationship filters, CLI, inspector, LangGraph/LangChain tools, MCP transport, updates/backup/GC, evaluator, authored fixtures, documentation and build scripts.

Verification: 52 Python tests pass on each of Python 3.11, 3.12 and 3.13; three browser workflows pass; lint, formatting, static typing and the viewer build pass. Local methods complete 1,260 recorded software-fixture comparisons without runtime failures. Scale fixtures cover 100–1,000 documents and bounded map pagination. Artifact installation and full-project smoke evidence are recorded in reports as verification finishes.

Scheduling exception: the user initially requested the entire local build and explicitly deferred real-model checks. On 2026-11-17 the user authorized a minimal-cost Claude API test; one answer smoke is recorded. Independent implementation and software checks proceeded beyond those external gates. Checked task deliverables are verified locally; this does not mark a milestone's deferred research/model/publication gate complete. The original milestone acceptance criteria remain in force.

Next acceptance work: independently reviewed pilot data, configured model/embedding checks, strong external reproductions, final study/protocol/claim, package-registry identity, dependency/asset compatibility review, and authorized registry publication/submission. GitHub source publication is authorized and MIT licensing is established; package-registry publishing and paper submission remain open.

2026-11-15 user-requested documentation/licensing refresh: T062 now has a friendly main README and a separate technical README. MIT license and package metadata are added; release/research scripts include it in future artifacts. Fresh core-only installation runs both Python examples and CLI/demo/backup flows; inspector build/serve, 56 local links/images, MCP JSON, wheel/source license inclusion, lock consistency and changed-script lint/format checks pass. Historical receipts are preserved. T060 remains open for package-registry identity and dependency/asset review; task counts are unchanged.

2026-11-17 T062 visual refresh, requested by the user: added a forest-green SVG banner, badges, section navigation, Mermaid workflow, feature/format/documentation tables, linked inspector preview, and collapsible setup instructions to the main README. Desktop/phone previews have working images and details, a rendered diagram, and no page-wide horizontal overflow. All 20 local links/images/anchors resolve; SVG parsing, source-archive banner inclusion/private-context exclusion, and diff whitespace checks pass. Task counts and remaining research/model/release gates are unchanged.

2026-11-17 T025 acceptance: user authorized a minimal-cost Claude model check. Added the opt-in Claude Messages adapter and shared structured-provider protocol; nine offline integration checks and the full 61-test suite pass, as do Ruff and mypy. One cited-answer smoke over one 120-byte authored passage passes with exact-byte/citation validation, 377 input + 63 output tokens, estimated $0.002768, and zero retries. Credential-free receipt: reports/anthropic-smoke.json. T025 is checked; 51 deliverables are checked and 14 broader acceptance tasks remain open. No additional paid calls are authorized by this record; full live navigation/enrichment, embeddings, research comparisons and release gates remain pending.

2026-11-17 T025/T062 correction requested by the user: extracted neutral model contracts, added an application-callable adapter and distinct SDK mapping examples, removed URL assumptions from caches/evaluation, exposed embedding primitives, and added CLI project factories. Updated integration/API guidance, rules, ADR 003 and durable Haiku preference. Full local suite now has 79 passing tests; lint/type/viewer checks and clean-wheel embedding in a separate project pass. No new paid requests; prior Opus receipt unchanged. Task counts remain 51 checked/14 open.

2026-11-17 T038/T039 recorded-run screenshot: an external Haiku native navconr_read call was dispatched through AgentTools and its exact evidence/tool trace captured in the unmodified inspector. See reports/haiku-tool-inspector.png and reports/haiku-tool-call.json. The user corrected the observability scope: final agent replies are not normal Navconr tool data; the proposed uncommitted reply panel was removed. One earlier answer-synthesis call plus the corrected native-tool call used an estimated $0.000196 total. The native tool capture is one forced read with application-prepared context, not full agent/research validation. Task counts and broader gates remain unchanged.
