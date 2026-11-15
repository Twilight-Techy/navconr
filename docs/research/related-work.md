# Related work and comparison candidates

This matrix describes mechanisms from primary sources. Reported performance is not independently reproduced here. Hierarchical indexing, source references, iterative exploration, and retrieval budgeting alone are not novelty claims.

| System | Mechanism | Overlap / comparison caveat |
| --- | --- | --- |
| [PageIndex](https://github.com/VectifyAI/PageIndex) | Document trees, model-directed retrieval, corpus navigation | Very close architectural overlap; compare only compatible source inputs and account for preprocessing and all model calls |
| [RAPTOR](https://arxiv.org/abs/2401.18059) | Recursively embed, cluster, summarize; retrieve at multiple levels | Summary-tree construction differs from physical hierarchy; report embedding and indexing-model costs |
| [LlamaIndex recursive retrieval](https://developers.llamaindex.ai/python/framework/integrations/retrievers/recursive_retriever_nodes/) | Retrieve reference nodes and follow them to content | Direct overlap with reference-to-evidence separation; preserve actual retrieval configuration |
| [GraphRAG DRIFT](https://microsoft.github.io/graphrag/query/drift_search/) | Community context and iterative local exploration | Entity/community graphs differ from source structure; expensive preprocessing must be accounted for |
| [IRCoT](https://arxiv.org/abs/2212.10509) | Interleave reasoning and retrieval | Agentic iteration precedes this project; compare under equal model budgets |
| [NavTree](https://arxiv.org/abs/2610.06902) | Navigation scaffold without LLM summaries | Challenges the need for generated summaries; use a no-summary ablation |

Candidate contribution to investigate: adaptive allocation of a fixed total budget among map inspection, alternate-branch exploration and source reads, with version-exact evidence. A systematic literature review and original-method reproductions remain required before claiming novelty. Internal structural-tree and parent-child baselines must not be presented as reproductions of named external systems.

Implementation comparisons should record upstream revision, supported inputs, configuration, models, prompts, source transformations, cached/uncached costs and failures. If credentials, dependencies or data are unavailable, emit an unavailable comparison entry, not an invented score.
