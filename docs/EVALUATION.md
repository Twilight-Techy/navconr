# Evaluation and reproducibility

`benchmarks/create_fixtures.py` generates fictional documentation and 70 authored questions across ten document families. Five families belong to `dev`, five to `heldout`; their partition is a software fixture split, not a claim of a human-reviewed held-out study. Gold passages are verified against original indexed bytes before scoring. Family and evidence-source leakage are rejected.

```bash
python benchmarks/create_fixtures.py
navconr ingest benchmarks/corpus --db .navconr/benchmark.sqlite
navconr evaluate benchmarks/dataset.json --db .navconr/benchmark.sqlite \
  --split dev --budgets 512 2048 --output benchmarks/results
```

The runner compares lexical, TF-IDF vector, lexical/vector hybrid, parent–child expansion, structural-only navigation, fixed/adaptive navigation, and no-summary/no-reference ablations. Source limits apply equally; total map output, steps and latency are also recorded. None of these local methods uses an LLM. Model-directed navigation and semantic embedding benchmarks require explicit separate configuration.

Outputs are content-keyed manifests, per-question JSONL results, JSON summaries and Markdown reports. Resume uses a key covering code, dataset, index revision and settings. A malformed partial row fails explicitly for recovery. Changes to source code intentionally create a new result directory rather than mixing runs. Preserve report manifests when citing a result.

Evidence recall measures how many required groups have at least one supported alternative passage recovered. Contiguous returned intervals are merged so chunk boundaries do not falsely lose a passage. Complete-evidence success requires all groups. Unanswerable fixtures measure absence of evidence, not nuanced real-world abstention. Exact source bytes and budget compliance are checked independently.

Answer correctness and citation entailment are null when no common reader/review is configured; they are never inferred from retrieval recall. Optional answer synthesis performs citation-ID validation only. A research study needs a shared reader, annotated answers, independent human review and suitable uncertainty estimates. Synthetic lexical queries are easy and can favor lexical methods; their results do not establish scientific superiority or generalization.

External PageIndex/RAPTOR/NavTree comparisons are reported as not run when upstream setup/models are unavailable. Internal structural baselines are not reproductions of those systems. The related-work matrix and protocol in `docs/research` define the remaining requirements.

`scripts/profile_scale.py` measures fictional corpora with 100, 500 and 1,000 sources, including ingestion, one-source updates, query cost, map pagination and SQLite size. RSS is a cumulative Linux process high-water mark. These measurements describe this environment and workload, not asymptotic scaling.

The user authorized a minimal-cost Claude API smoke check. [The recorded run](../reports/anthropic-smoke.json) uses one 120-byte authored passage, one generation request, 377 input tokens and 63 output tokens. Exact-byte and citation-membership checks pass; estimated cost is $0.002768 at the recorded price. This validates a narrow retrieval-to-answer integration. Multi-step model-directed navigation, enrichment, comparative model/answer-quality studies, and embedding downloads remain unrun. Mocked-provider checks and this one authored example do not replace the independent research study.

External runs can be imported with `scripts/score_external.py`. The schema in `navconr.external.ExternalRun` requires upstream revision, configuration, source transformations, pinned index revision, budget, and exact returned spans. The importer checks snapshot/coordinate compatibility and budgets; supplied usage/latency remain producer-reported. It does not claim to execute upstream systems.
