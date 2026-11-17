# Embed Navconr in an existing project

Navconr is an installable Python library. Indexing, maps, search, evidence reads and traces run without a model. Your application owns model selection, credentials, SDK clients, message formats, deployment and agent policy. The CLI, inspector, model adapters and framework integrations are optional entry points.

## Use your existing agent

Keep the model calls and agent loop in your application. Give it Navconr's bounded tools:

```python
from navconr import AgentTools, Index, Limits, ToolRequest

with Index("knowledge.sqlite") as index:
    index.ingest("docs")
    tools = AgentTools(index)
    session = tools.begin(Limits(source_bytes=4096, steps=32))
    result = tools.call(ToolRequest(
        session_id=session["session_id"],
        operation="search",
        arguments={"query": "authentication"},
    ))
    print(result)
    tools.close(session["session_id"])
```

`AgentTools.schemas()` supplies neutral JSON schemas. Register them in your agent's tool format, then dispatch allowed calls through `AgentTools.call`. This path does not require a Navconr model provider or change your request format. Keep the session open for the agent's workflow so its revision and budgets are shared. See [API](API.md) for overview, expand, search, follow and exact reads.

Projects in other languages can use the optional [MCP stdio interface](API.md). Python applications can call `Index` and `Session` directly without any agent framework, server or inspector.

The tool integration observes Navconr invocations, arguments, returned evidence and its own usage limits. It does not observe the host agent's final assistant reply, prompts, thinking, provider identity or model-token usage automatically. A host can explicitly supply additional metadata, but normal inspector traces show tool activity. The separate optional answer-synthesis helper has access only to replies it explicitly requests itself.

An actual external Haiku `navconr_read` capture is shown in the [inspector screenshot](../reports/haiku-tool-inspector.png), with a separate [host-side receipt](../reports/haiku-tool-call.json). The application code is [capture_haiku_tool_run.py](../scripts/capture_haiku_tool_run.py): it registers a native tool, dispatches the generated call through `AgentTools`, and saves only tool invocations/results for replay. This is a single forced read call with application-prepared navigation context, not a full autonomous agent evaluation. Running the script is an explicit paid action; viewing/replaying the recorded result is free.

## Use Navconr's optional model components

For the reference controller, answer synthesis or enrichment, wrap an existing async application function:

```python
from navconr import CallableProvider, ModelRequest, ModelResponse

async def complete(request: ModelRequest) -> ModelResponse:
    # Your code chooses the SDK/wire format and extracts the result.
    result = await existing_client.generate(
        payload=request.prompt,
        schema=request.response_schema,
        output_limit=request.max_output_tokens,
        timeout=request.timeout_seconds,
    )
    return ModelResponse(
        content=result.parsed_object,  # dict or JSON text
        input_tokens=result.total_input_tokens,
        output_tokens=result.total_output_tokens,
    )

provider = CallableProvider(
    complete,
    name="my-project-model",
    cache_key="my-model-and-prompt-config-v1",
    max_output_tokens=256,
)
```

`existing_client.generate` above illustrates an application-specific interface; Navconr does not require a client with that method. Map any client or service into this four-field request/two-part response contract. A callback can parse a tool response, JSON, or another wire representation into a dictionary. No provider URL, vendor name, HTTP headers, or specific message envelope is required.

Pass the resulting provider to `Navigator(index, policy="model", provider=provider)`, `answer`, `enrich`, `infer_pairs`, or the evaluator's `reader`. Domain schemas such as `Action` and `Answer` describe Navconr operations, independently of the external request format. You may also implement `StructuredProvider`/`PolicyProvider` directly if your project needs custom accounting.

Concrete mapping examples for application-owned async [OpenAI Responses](https://developers.openai.com/api/reference/python/resources/responses/methods/create) and [Anthropic Messages](https://platform.claude.com/docs/en/api/http/messages/create) clients are in [provider_clients.py](../examples/provider_clients.py). They import no vendor SDK and make no calls on import. Their distinct request/response mappings are tested offline; this is not a live cross-provider evaluation. Install/configure your SDK in your own project, then call the appropriate helper with your client, chosen model and a safe configuration identity.

## Budgets and ownership

The callable adapter reserves before invoking the callback, applies a deadline, validates returned data, reconciles usage and never automatically retries. The callback must pass the supplied output cap and timeout to its SDK and disable hidden SDK retries. Cancellation cannot guarantee that a remote service stops computing. A synchronous SDK can be called from an async wrapper using `asyncio.to_thread`; the wrapper must still configure the SDK timeout because cancellation does not stop the worker thread.

Return total input/output counts, including cached input and reasoning tokens, when available. Missing counts are estimated explicitly: known counts are retained, absent input uses the configured estimate, and absent output uses its reserved cap. If both counts are absent the full reservation is charged. A custom `estimate_input_tokens` callable can include your SDK's framing overhead; the default estimates serialized prompt/schema bytes plus an allowance. Hard total-token guarantees are rejected by the generic adapter. An SDK that ignores limits cannot be made safe merely by wrapping it; implement the contract at the actual request boundary.

Provider `cache_key` is an opaque, credential-free identity for model/configuration/prompt version. Change it when relevant settings change. Custom protocol implementations may omit it if `name` itself uniquely identifies the configuration. Enrichment and evaluation use this identity without inspecting provider URLs or SDK objects.

## CLI with your project configuration

Expose a zero-argument factory returning your provider, for example `myapp.navconr_config:create_provider`, and keep `myapp` importable in the environment:

```bash
navconr query "your question" --policy model \
  --provider-factory myapp.navconr_config:create_provider --db knowledge.sqlite
navconr enrich --provider-factory myapp.navconr_config:create_provider --db knowledge.sqlite
navconr evaluate questions.json --reader-provider-factory myapp.navconr_config:create_provider \
  --db knowledge.sqlite
```

The factory configures the application client and returns `CallableProvider` or a protocol implementation. Credentials stay in application configuration. The explicit factory runs application code you selected. Existing `--model`/`--endpoint` options remain an Ollama convenience; factory flags select your own integration without those options.
