# ADR 003: application-owned model clients and wire formats

Status: accepted, 2026-11-17.

The user reaffirmed that Navconr must embed in existing projects independently of model vendor and request format. The initial indexing/tool core already ran without an LLM, but optional enrichment/evaluation required `base_url`, CLI model selection constructed Ollama directly, and the primary examples emphasized built-in adapters.

Core protocols now live in `navconr.model` without concrete provider imports. `StructuredProvider` requires a name and a structured operation, while `PolicyProvider` requires a name and an action operation. An optional opaque configuration identity supports cache isolation; endpoint inspection is removed from core consumers. Built-in adapters derive their own safe identities. Legacy protocol imports remain available.

`CallableProvider` maps an application-owned async function onto the contracts. It passes a domain prompt, response schema, output cap and deadline, then validates normalized JSON/dictionary output and reconciles reported usage. The application owns SDK/wire serialization, credentials, model choice, response extraction and enforcement of request limits. SDK retries must be disabled. Unknown usage is estimated conservatively and unsupported hard token guarantees fail closed. No generic adapter can force an opaque client or remote service to honor its limits.

Existing agent loops can instead use `Index`, `Session`, or `AgentTools` without involving the optional controller or any model adapter. MCP provides a separate language-neutral transport. CLI provider factories load the application's configuration for navigation, enrichment and answer evaluation; Ollama flags remain a backward-compatible convenience.

The root package exports the embedding interfaces. Application-owned OpenAI Responses and Anthropic Messages mapping examples are tested offline with distinct envelopes. A clean installed wheel also runs from a separate consumer project without either SDK. These checks establish integration behavior, not live provider parity or a research result.

Paid smoke defaults now prefer Haiku, as explicitly requested by the user. No new paid call was made for this correction. The earlier Opus receipt is preserved as historical evidence.
