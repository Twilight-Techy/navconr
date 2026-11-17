# Public API and integration guide

`Index(path)` owns a SQLite connection. Use it as a context manager or close it explicitly. `Index.ingest(root, block_bytes=2048, enricher=None)` publishes a complete revision, reuses unchanged source parsing when configuration matches, and preserves original bytes.

`Index.session(revision=None, limits=None, encoder=None)` pins a revision and shares one budget across its tools. Convenience `Index.overview/search/expand/follow/read` each create a fresh session. Agent applications should keep a session rather than call convenience tools to simulate a shared budget.

| Session method | Inputs | Result |
| --- | --- | --- |
| `overview` | limit, cursor, max_bytes, physical/semantic view | Bounded collection cards |
| `expand` | node_ids, paging controls | Physical children or semantic group members |
| `search` | query, lexical/vector/hybrid/semantic mode, optional scope, paging | Ranked source-block cards |
| `follow` | node_id, relation, inverse, paging | Related cards and unresolved references |
| `read` | span_ids, optional explicit absolute-byte subranges | Exact evidence or per-item error |

For paging, repeat the same arguments and pass the returned cursor. Changing operation, query, revision, limit, or max_bytes invalidates the cursor. A response that cannot fit one card fails explicitly. Reads never silently shorten text. Source bytes and map-response bytes use separate exact limits; model-token accounting has explicitly declared estimates.

```python
import asyncio
from navconr import Index, Limits
from navconr.navigation import Navigator

async def research():
    with Index('.navconr/demo.sqlite') as index:
        result = await Navigator(index).retrieve(
            'refresh token revocation',
            limits=Limits(source_bytes=4096, steps=64, seconds=30),
        )
        assert all(item.revision == result.revision for item in result.evidence)
        return result

result = asyncio.run(research())
```

Inside an existing event loop, use `await research()` rather than `asyncio.run`. Local SQLite operations are synchronous and single-connection; do not share an `Index` across threads. Use independent connections and revision-pinned sessions. Network provider operations are async and propagate cancellation/deadlines.

`Navigator` accepts fixed, adaptive, or model policies; `search_mode`, `summaries`, `references`, and `global_search` allow controlled ablations. Adaptive routing is currently a simple budget-dependent expansion/stopping heuristic, not a learned planner. Completion means the policy stopped; it is not a proof that all evidence was recovered.

`Index.group_topics()` creates deterministic cross-document groups from shared headings; `navconr topics` exposes it in the CLI. `Index.group(title, node_ids)` adds a semantic group without changing physical parents. `Index.link(edges)` validates and publishes explicit/manual/inferred relationships. `navconr.relationships.suggest_related` proposes optional cross-source TF-IDF cosine edges with origin `similarity`; scores are not calibrated probabilities. Callers decide whether to publish them. Changed targets become explicit stale references during later ingestion.

`SentenceEncoder` is an optional adapter from `navconr.search` and needs `navconr[embeddings]`. Configure a model revision for reproducibility. Its first use may download model weights. The CLI's default vector mode uses TF-IDF, not learned embeddings; semantic CLI search needs a custom configured library session and otherwise fails clearly.

Optional model components:

```python
from navconr.budget import Budget
from navconr.providers import OllamaProvider
from navconr.enrichment import enrich
from navconr.answering import answer

provider = OllamaProvider('your-model')
# await enrich(index, provider, Budget(Limits(model_calls=100, model_tokens=50000)))
# response = await answer(question, retrieval_result, provider, Budget())
```

Enrichment is atomic and cannot alter source spans. Answer synthesis validates that citations name retrieved spans and requires citations for a non-abstaining answer. This structural validation does not establish that a claim is entailed by its citation; answer quality still needs evaluation. No evidence causes local abstention without a model call.

The Ollama adapter reserves byte-based input estimates and provider-limited outputs, reconciles reported usage, and charges failed requests conservatively. It rejects `hard_model_tokens=True` before a request because it has no trusted preflight tokenizer. Cancellation cannot guarantee that a remote server stops computing after the client disconnects.

### Minimal Claude integration

`AnthropicProvider` from `navconr.anthropic` implements the same `structured`/`action` interface. `answer`, `enrich`, relationship inference and evaluation accept the shared `StructuredProvider` protocol; `Navigator` accepts its action interface. No additional SDK dependency is needed.

```python
import os
from navconr.anthropic import AnthropicProvider

provider = AnthropicProvider(
    "claude-opus-5-5",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_input_tokens=600,
    max_output_tokens=160,
)
```

The adapter sends only to `https://api.anthropic.com`, uses API version `2026-10-21`, low effort, standard service, terse JSON prompts, a free token-count preflight, and provider-enforced output bounds. It fails before generation when the preflight exceeds the input cap. Token counts are estimates before execution, so a requested hard total-token guarantee is rejected. It never automatically retries or follows redirects; failed generation attempts consume their reservations conservatively. Only text output and token totals are retained; thinking blocks and raw HTTP error bodies are discarded. API keys stay in request headers and are not part of prompts, traces, cache keys or receipts. The CLI's model options currently configure Ollama; use Python for Claude.

The explicit paid smoke command is `.venv/bin/python scripts/smoke_anthropic.py`. It reads `ANTHROPIC_API_KEY` or prompts with hidden input, retrieves one short authored passage, verifies exact source bytes, asks for one cited answer, and writes a credential-free receipt. It permits one generation, 160 output tokens, zero retries and a 45-second deadline. It is excluded from ordinary tests/CI. Running it again can spend credits; the existing [receipt](../reports/anthropic-smoke.json) records the completed run. Broader live navigation/enrichment remains unverified.

Protocol and pricing references: [Anthropic Messages API](https://platform.claude.com/docs/en/api/http/messages/create), [free token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting), and [Opus 5.5 pricing](https://platform.claude.com/docs/en/models/opus-5-5/overview).

`AgentTools.begin`, `call`, and `close` form the framework-neutral integration. Tool argument schemas are available from `AgentTools.schemas()`; only overview/expand/search/follow/read are allowed. Each session has independent limits, an immutable revision, and a deadline. The optional MCP transport exposes these same operations:

```json
{"mcpServers":{"navconr":{"command":"/absolute/path/to/.venv/bin/navconr","args":["mcp","--db","/absolute/path/to/index.sqlite"]}}}
```

`navconr schemas` exports the executable record schemas. Records reject unknown fields. Schema 1 is the first development schema and may change before the first stable release.

`navconr.relationships.infer_pairs` optionally asks a configured provider about known node pairs and returns inferred edges without inventing endpoints; publish validated candidates explicitly. `evaluate(..., reader=provider)` or CLI `evaluate --reader-model MODEL` uses one configured answer reader across methods. Questions can supply `expected_answers` for exact normalized matching. Citation entailment and synthesis quality still require reviewed assessment.

Install `navconr[langgraph]` to use `langchain_tools(index)` (three async tools sharing the core ledger) or `retrieval_graph(index)` (a reference context-retrieval workflow). Run `python examples/langgraph_context.py` for a real LangGraph workflow with no LLM. Use the tools with an existing agent model when configured; the runtime check here validates framework integration, not a live-model agent. Keep the Index and async tool calls on the same event-loop thread.
