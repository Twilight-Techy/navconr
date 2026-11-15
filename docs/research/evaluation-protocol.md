# Evaluation protocol v1 (before controller tuning)

Question: under fixed retrieval budgets, when does progressive navigation improve evidence coverage relative to strong search?

Use original, redistributable technical documentation fixtures grouped into document families. Questions include direct lookup, cross-section/multi-document evidence, distractor branches and unanswerable queries. Every question declares its split, required evidence groups, acceptable alternative passages and answerability. Development and held-out families must be disjoint. Labels and answers never enter enrichment or navigation prompts.

Initial smoke data are authored fixtures with machine-checked passage labels. They test software, not scientific generalization. A 50–100 question pilot with genuinely independent human review remains a separate acceptance gate; do not imply that authored synthetic fixtures meet it.

Freeze dataset hashes, method settings, random seeds, source byte budgets and repeated runs in manifests. Compare FTS5, TF-IDF cosine (lexical vectors), reciprocal-rank hybrid, parent-child expansion, structural tree navigation, fixed navigation, adaptive navigation, and optional learned embeddings. TF-IDF is not a semantic embedding model. External systems are separate optional reproductions with explicit status.

Score required-group recall: a group is recovered when one alternative source passage is present in exact returned evidence. Score complete-evidence success only if all groups are found. Also report evidence bytes, source count, redundancy, correct abstention on unanswerable questions, errors, p50/p95 latency, total model input/output tokens, calls, output bytes and indexing/update overhead. Answer correctness/citation support require an optional common reader and reviewed labels; do not substitute retrieval recall for answer quality.

Use at least two source budgets and fixed seeds. Ablate summaries, reference traversal, hierarchy and adaptive stopping. Compare all methods using the same source representations and evaluation harness; label approximations. Persist raw per-question results and resume only when the full configuration/input hash matches. Report cold indexing and warm queries separately.

Correctness gates: exact evidence, revision isolation, no unreported failures, hard byte budgets, and valid split manifests. Select empirical performance targets after the development pilot, before unblinding held-out results. No targets or held-out superiority are assumed in advance. Hosted-model checks require explicit configuration and honest measured-vs-estimated usage reporting.
