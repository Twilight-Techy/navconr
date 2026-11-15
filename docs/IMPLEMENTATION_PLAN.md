# End-to-end implementation plan

Status: planning baseline, established 2026-11-15. See [TASKS.md](TASKS.md) for execution status and [MEMORY.md](MEMORY.md) for decisions. This file describes intended behavior; it does not claim an implementation exists.

## 1. Outcome and scope

Deliver Navconr as an installable library for progressive, source-grounded knowledge navigation. An application ingests a collection, obtains a bounded overview, explores relevant branches and references, and reads exact evidence. Applications can use the tools directly or use a supplied budgeted navigation controller.

The complete project includes:

- Immutable source storage and exact source/extraction locators.
- Structural ingestion, optional semantic enrichment, hierarchical maps, and typed cross-links.
- Bounded navigation tools and lexical/vector/hybrid search adapters.
- A reference controller with multi-branch exploration, recovery, budgets, and replayable traces.
- An evaluator with strong baselines, evidence annotations, ablations, and reproducible reports.
- An inspector for structure, source evidence, and retrieval paths.
- Incremental maintenance, revision management, migrations, and operational diagnostics.
- Markdown, text-based PDF, code, HTML, DOCX, and notebook adapters.
- A CLI, agent tool schemas, a reference integration, and an optional MCP server.
- Public-release artifacts and a research paper supported by actual findings.

The first prototype covers Markdown collections and local use. Scanned-document OCR, image understanding, distributed indexing, multi-tenant hosted services, and learned routing policies are extensions after the first release. Keep extension points, but do not build those services as prerequisites.

Success is a usable system with reliable evidence and measured tradeoffs. It does not require beating every baseline. A paper may report negative or conditional results if the experiments support them.

## 2. Working architecture

```text
Source adapters
  → immutable original snapshots and extraction artifacts
  → parsed physical structure and exact spans
  → bounded blocks, explicit references, optional semantic enrichment
  → physical hierarchy + semantic navigation maps + typed relationships
  → versioned local index and optional search indexes

Application / agent / CLI
  → navigation tools OR reference navigation controller
  → shared budget and revision context
  → bounded map responses and exact source reads
  → evidence result + action trace + usage + stop reason

Evaluator and inspector consume the same exports, events, and evidence.
```

The physical hierarchy describes where content lives. Semantic maps describe useful ways to navigate it. Neither replaces the original source. A source has one physical organization per parser revision, while semantic nodes may group spans from unrelated physical branches.

Start with SQLite tables and adjacency queries. The storage interface leaves room for other backends. A graph database is optional. Providers, search strategies, enrichment, and agent frameworks remain replaceable.

### Components and boundaries

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Source repository | Store immutable original bytes, extracted artifacts, revisions, and hashes | Rewrite evidence during reads |
| Parser adapter | Extract structural blocks, locators, and explicit references | Assign model-inferred facts as verified structure |
| Enricher | Produce bounded summaries, labels, and candidate relationships | Fabricate source positions or valid target IDs |
| Map builder | Construct bounded navigation layers and cross-links | Require the entire collection map in one response |
| Index store | Persist sources, spans, nodes, edges, revisions, and caches | Expose a partially published revision |
| Search adapter | Return ranked navigation candidates with provenance | Silently change the controller's source revision |
| Tool layer | Validate and execute bounded, versioned operations | Bypass usage accounting or root restrictions |
| Navigation policy | Select exploration, search, reading, and stopping actions | Depend on UI code or a particular agent framework |
| Budget manager | Reserve, reconcile, and terminate work under limits | Present estimated usage as exact |
| Trace writer | Record operations and results for inspection/replay | Require hidden reasoning or leak credentials |
| Evaluation runner | Execute controlled comparisons and score evidence/answers | Tune against held-out answers |
| Inspector | Display maps, locators, and observed action paths | Invent retrieval explanations absent from recorded events |

### Proposed package layout

Freeze exact names in T006–T007. Keep package boundaries aligned with responsibilities:

```text
src/navconr/
  models/           # source, span, node, relationship, result, budget, event
  sources/          # snapshots, extraction artifacts, locator resolution
  parsers/          # format adapters
  ingestion/        # segmentation, enrichment, mapping, revision publication
  storage/          # protocols, SQLite implementation, migrations
  search/           # lexical, vector, hybrid adapters
  tools/            # bounded navigation/read contracts
  navigation/       # reference controller and policies
  providers/        # optional model adapters and usage capabilities
  tracing/          # events, export, replay, redaction
  cli/
  integrations/     # thin framework/MCP adapters; optional extras
tests/
benchmarks/         # fixtures/manifests, annotations, runners, reports
examples/
viewer/             # optional UI, separately built and distributed
docs/
```

Use Python with Pydantic for schemas, `markdown-it-py` for initial parsing, and SQLite FTS5 for lexical retrieval. The optional inspector uses React and React Flow. Final supported versions, dependency constraints, and packaging choices are set during scaffolding, not guessed here.

## 3. Data and API contracts

### Records

| Record | Required concepts |
| --- | --- |
| SourceRevision | Logical source ID, revision hash, media type, original blob reference, parser/config version |
| ExtractionArtifact | Original revision, extractor/version, extracted blob/hash, mapping to original pages/elements/cells |
| Span | Source/artifact revision, explicit locator kind, start/end or element identity, optional display coordinates |
| NodeRevision | Logical/revision IDs, node kind, bounded title/summary, source span references, physical/semantic membership |
| Relationship | Source/target node revisions, type, origin, evidence references, optional inference score |
| IndexRevision | Published revision, constituent source/node revisions, configuration fingerprints, creation provenance |
| RetrievalBudget | Limits for calls, steps, tokens, map output, source output, expansions, retries, and deadline |
| TraceEvent | Sequence, action, index revision, selected IDs, response references, timing, usage, outcome |
| RetrievalResult | Evidence spans, coverage limitations, trace reference, measured/estimated usage, stop reason |

Relationship types initially include physical containment, semantic membership, explicit reference, and adjacency. Add inferred relatedness and code-specific edges with provenance at their milestones. Define directedness and inverse-query semantics in the schema.

Logical identity and content identity are different. A rename may retain a logical source identity if explicitly detected; a changed source produces a new immutable revision. Never promise stable semantic-node identity across arbitrary edits. Preserve ancestry and mark unresolved identities when matching is uncertain.

### Tool surface

The names below are proposed contracts. T003 and T022 finalize request/response schemas before integration:

```python
index.overview(revision=..., cursor=..., budget=...)
index.expand(node_ids=[...], cursor=..., budget=...)
index.search(query, scope=..., mode=..., cursor=..., budget=...)
index.follow(node_id, relation=..., cursor=..., budget=...)
index.read(span_ids=[...], budget=...)

await navigator.retrieve(query, revision=..., budget=...)
```

Map operations return bounded node cards and continuation information. Reads return exact evidence, revisioned locators, and explicit indicators when a requested result does not fit. The API must let callers select a smaller range or page through evidence without silently truncating it. Batched requests preserve per-item outcomes and use shared accounting.

The core returns evidence and a trace. Answer generation is an optional layer so retrieval quality can be evaluated independently. Answers must cite resolved evidence and handle missing or contradictory information explicitly.

Typed errors cover invalid IDs/ranges, unavailable revisions, incompatible schemas, unsupported formats, unresolved references, missing provider capabilities, and corrupt storage. Stop reasons cover successful policy completion, exhausted budgets, deadlines, cancellation, insufficient evidence, and failures. A policy's successful completion is not proof that all relevant evidence was found.

## 4. Execution milestones

Tasks execute in the listed order by default. Within a milestone, readiness follows explicit task dependencies. The gates below determine when later work is justified.

### M0 — Establish contracts and evaluation design (T001–T006)

Define intended users, scenarios, scope, failure behavior, terminology, schemas, source-coordinate contracts, and research comparisons. Review closely related systems rather than treating hierarchy or agentic retrieval as new. Design pilot questions and annotations before tuning retrieval.

Deliverables: product brief, related-work matrix, initial architecture decisions, schema specifications, locator specification, and evaluation protocol. Place evolving design documents in `docs/design/`, architecture decisions in `docs/decisions/`, and research notes in `docs/research/` as tasks require them.

Exit: each central object has a concrete example; evidence can be located without ambiguity; the pilot and its baseline/budget rules are specified; unknowns have a resolution task. No dependency on paid providers.

### M1 — Build the minimal core (T007–T011)

Create the package, validation tooling, local test fixtures, CI checks, schemas, SQLite storage, immutable snapshots, and trace/usage records. Implement schema-version detection and transaction boundaries early.

Exit: a clean environment can install the package, create and reopen an index, store/read original bytes, reject invalid records, and round-trip versioned exports. Unicode and newline fixtures resolve to exact bytes.

### M2 — Ingest Markdown collections (T012–T017)

Parse physical structure and explicit links, segment large content while preserving locators, add optional bounded enrichment, and construct navigation layers. Keep tables, lists, and code fences intact where possible; define deterministic fallback behavior for oversized atomic blocks. Build an unenriched index with structural titles when no model is configured.

The collection root must stay bounded even with many documents. Grouping may use folders, metadata, or deterministic partitions initially; preserve physical paths separately. Cache enrichment by content/configuration and publish only complete index revisions.

Exit: Markdown fixtures ingest repeatably; every source block is accounted for or explicitly excluded with a reason; there are no invented spans; unresolved links are visible; a large sibling set never forces a giant overview.

### M3 — Expose navigable evidence tools (T018–T023)

Implement bounded overview, expansion, lexical search, typed reference following, and exact span reading. Validate all tool outputs and make revision/cursor behavior explicit. Provide a developer example that navigates a collection manually before adding autonomous control.

Exit: an application can find and read evidence across multiple documents using only public tools. Unknown IDs, stale cursors, wrong revisions, and excessive response requests fail predictably. Reading returns original text without rewriting it.

### M4 — Add the budgeted reference controller (T024–T029)

Implement shared reservations/accounting and a cancellable provider adapter. Begin with a fixed, inspectable policy: inspect overview, select a bounded frontier, expand or search, read evidence, and stop under explicit rules. Support several branches, global recovery search, deduplication, and cycle prevention.

Provide fake-provider deterministic integration tests and a small opt-in real-provider smoke run. Build trace replay before tuning adaptive behavior. Add semantic grouping and summary-aware routing as switchable strategies.

Exit: the Markdown prototype works end to end. It recovers from a misleading branch, uses a cross-document reference, handles absent evidence, and terminates under all configured budgets. Every action and source is inspectable. Unsupported hard-budget guarantees are reported before execution.

### M5 — Evaluate the prototype and choose its next policies (T030–T035)

Create approximately 50–100 manually reviewed pilot questions as a feasibility starting point, sized to annotation resources. Include direct lookup, multi-section synthesis, cross-document evidence, distractor branches, and unanswerable cases. Record alternate valid evidence sets and annotation uncertainty.

Implement lexical, vector, hybrid, parent–child, and structural-tree baselines over comparable parsed source material. Use identical readers and answer prompts where answers are evaluated. Measure retrieval alone and complete answer generation separately.

Run ablations and error analysis. Establish empirical quality/cost targets before opening held-out evaluation. Keep indexing cost, query cost, cache state, and cost amortization assumptions visible.

Exit: a reproducible report explains successes, failures, and costs. A second clean run reproduces the local metrics within defined tolerances. The team can decide whether adaptive routing, more summaries, or richer edges deserve investment. Failure to show a quality gain is a finding, not permission to change the evaluation silently.

### M6 — Build the inspection and visualization layer (T036–T039)

Export stable map and trace views. Build an expandable tree/graph display, source panel, relationship-origin filters, and action playback. Lazy-load bounded regions; do not render the whole corpus at once. Highlight selected branches, dead ends, fetched evidence, and usage over time.

Start with saved exports, then add a read-only local bridge for live inspection. Keep viewer dependencies outside the Python core. Redact secrets and support source-free exports for sharing.

Exit: a developer can diagnose a wrong branch and inspect the exact supporting text from a recorded run. The inspector tolerates large maps through bounded loading and handles unsupported trace versions explicitly.

### M7 — Make updates and operations reliable (T040–T044)

Implement source additions, edits, deletions, and rename handling. Recompute affected maps, summaries, relationships, and search entries while reusing valid cached artifacts. Readers stay on a consistent index revision during publication.

Add retention, backup/restore, migrations, bounded indexing concurrency, recovery diagnostics, and scale profiling. Decide transaction/journal behavior based on the single-writer/multiple-reader deployment model. Document any concurrency limits rather than promising distributed behavior.

Exit: interrupted updates preserve a usable index; pinned historical evidence remains readable; deleted content leaves current retrieval results; migration/restore tests pass; scale reports show resource growth and navigation overhead without assuming logarithmic behavior.

### M8 — Extend source types and retrieval choices (T045–T051)

Add text-based PDFs with page/extraction locators, code with syntax structure, and HTML/DOCX/notebook adapters. Format support is explicit: tables, malformed input, unsupported syntax, embedded objects, and image-only content have documented behavior. Resolve code imports/symbol references only where supported; do not advertise a complete call graph from syntax alone.

Add optional inferred relationships and production vector/hybrid search adapters, reusing evaluation code where appropriate. Validate mixed-format collections and build compatible comparisons against PageIndex, RAPTOR-style retrieval, and other closest methods selected in the review. Record exact implementations or label reimplementations.

Exit: each supported adapter has fidelity/locator tests and a realistic example. Mixed-format navigation preserves source provenance. Unsupported inputs fail clearly. Hierarchical comparisons disclose conversion, preprocessing, model, and budget differences.

### M9 — Stabilize integration surfaces (T052–T055)

Stabilize the Python API, CLI commands, tool schemas, and async behavior. Provide a minimal reference agent integration and optional MCP server. Core navigation remains usable without those integrations.

Local integrations explicitly configure source roots and provider access. The MCP adapter exposes bounded operations, validates inputs, and does not grant arbitrary filesystem or command execution. Develop examples without requiring a public service.

Exit: a new user can install the package, index a fixture, navigate/read evidence, inspect a trace, and connect an agent using documented commands. Error and cancellation behavior survive the integration boundary.

### M10 — Complete the research study and paper (T056–T059)

Finish the related-work review, select the actual research claim, and freeze the held-out experiment protocol. Determine adequate sample sizes and repeats from pilot variance and annotation capacity. Evaluate relevant public benchmarks only when their data and evidence structure fit the claim.

Run complete comparisons and ablations. Report uncertainty and paired comparisons where applicable, failures, abstentions, and indexing/query tradeoffs. Evaluate the adaptive policy against the fixed controller under the same budgets. Avoid changing models between methods without a separate controlled experiment.

Prepare the paper, figures, tables, scripts, run manifests, data/annotation documentation, and reproduction instructions. Explain limits on hosted-model repeatability and unavailable copyrighted/private data.

Exit: the paper's claims are traceable to recorded runs; a clean-environment reproduction is reviewed; no result is invented to fill missing experiments. Submission remains a separate authorized action.

### M11 — Prepare release, publish when authorized, and hand off (T060–T065)

Resolve distribution identity and license, audit dependencies and publishable assets, complete the API/reference/tutorial documentation, and build release artifacts. Test installation from the built artifacts, optional extras, CLI, schema compatibility, migrations, and representative examples.

Prepare a versioned release candidate, changelog, limitations, performance report, contribution guide, and maintenance policy. A hosted service is optional and not needed for library release. If requested later, plan its authentication, deployment, backups, and operating costs separately.

Exit: an approved package release can be installed and verified; public examples and research artifacts resolve; the paper is ready for or has completed authorized submission; memory records released versions and outstanding follow-up work. Lack of publication authorization means the artifacts remain ready locally, not that publishing has happened.

## 5. Verification strategy

| Layer | Checks that matter |
| --- | --- |
| Source fidelity | Unicode, CRLF/LF, repeated text, empty files, disjoint spans, original binary vs extraction coordinates |
| Parsing | Heading nesting, links/fragments, fenced code, tables/lists, malformed/oversized blocks, full coverage accounting |
| Persistence | Atomic revision publication, reopen/restore, foreign references, migrations, snapshot retention |
| Tool contracts | Bounded pages, cursor/revision mismatch, exact reads, invalid IDs/ranges, batched partial failures |
| Controller | Wrong-branch recovery, cross-document discovery, cycles, duplicate evidence, absent/contradictory evidence |
| Budgets | Reservations, repeated prompts, parallel work, retries, provider errors, deadlines, cancellation, unavailable usage |
| Safety boundaries | Root traversal/symlinks, retrieved prompt injection, credential redaction, untrusted imported artifacts |
| Evaluation | Split integrity, independent evidence labels, alternate evidence, accounting fairness, deterministic scoring |
| Viewer/integrations | Lazy loading, version errors, source fidelity, agent-visible stop reasons, cancellation propagation |
| Release | Fresh install, artifact contents, optional extras, migrations, documentation examples, known limitations |

Use focused unit/contract tests and end-to-end fixtures. Do not require a real LLM for routine CI. Real-model checks are explicit experiments with manifests and cost controls.

## 6. Evaluation metrics and decision rules

Primary retrieval metric: recall of required evidence at a fixed source budget, including whether all hops in an evidence set were recovered. Define span overlap and acceptable alternate evidence before scoring. Report precision/redundancy and source attribution as complementary metrics.

Answer metrics: task-appropriate correctness, citation support, unsupported claims, and appropriate abstention. Use deterministic checks where possible and human review for ambiguous synthesis. An LLM judge may assist but is not the sole unchecked authority.

Efficiency metrics: total input/output tokens across all navigation and answer calls, calls/steps, p50/p95 latency, indexing/enrichment cost, index size, update cost, and cached/uncached behavior. Compare several budget levels and show quality/cost curves. If embedding/search costs are nontrivial, include them as well.

Correctness gates are absolute: evidence fidelity, revision integrity, bounded outputs, and declared budget semantics must pass. Quality targets are fixed after the pilot and before held-out evaluation. Record the threshold, rationale, and comparison method in an architecture/evaluation decision. Performance regressions require investigation or a documented tradeoff; do not bury them in aggregate scores.

## 7. Risks and planned responses

| Risk | Response and relevant milestone |
| --- | --- |
| Summaries hide rare but important evidence | Global lexical/hybrid recovery, multi-branch routing, summary ablations; M4–M5 |
| Navigation costs exceed saved context | Count every call and token, batch expansions, compare budgets and caching; M4–M5 |
| Top-level index grows without bound | Bounded cards, grouping, pagination, fan-out stress tests; M2–M3 |
| Inferred cross-links mislead the agent | Preserve provenance, validate targets, separate explicit/inferred-edge experiments; M2/M8 |
| Edits break old citations | Immutable snapshots and revision-pinned retrieval; M1/M7 |
| Format conversion loses provenance | Explicit extraction artifacts and format-specific fidelity tests; M8 |
| Scope expands before the hypothesis is tested | Markdown vertical slice and pilot gate before broad adapters; M0–M5 |
| Proposed contribution duplicates prior work | Related-work matrix and claim freeze before paper; M0/M10 |
| Viewer becomes a separate product | Drive it from shared exports/traces and keep a narrow inspector scope; M6 |
| Hosted provider semantics prevent strict limits | Capability declarations, reservations, explicit supported guarantees; M4 |
| Benchmark results depend on preprocessing/model choices | Matched configurations, versioned manifests, disclosure and ablations; M5/M10 |

## 8. Completion and future extensions

The project is implementation-complete when the supported library, adapters, inspector, integrations, documentation, and evaluation artifacts pass their gates and the paper is evidence-backed and submission-ready. Public publication/submission tasks have their own authorization and verification gates.

After release, prioritize extensions using reported failures and measured costs. Candidates include scanned PDFs/OCR, multimodal evidence, additional languages, remote storage, learned routing, richer semantic maps, distributed indexing, and a hosted product. Each needs a scoped design and evaluation; none is silently included in the first release.
