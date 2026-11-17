import asyncio
import json
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from navconr import CallableProvider, Limits, ModelResponse, Navigator
from navconr.budget import Budget
from navconr.cli import main as cli
from navconr.enrichment import enrich
from navconr.models import BudgetExceeded, DeadlineExceeded, NavconrError

ROOT = Path(__file__).resolve().parents[1]
CLIENTS = runpy.run_path(str(ROOT / "examples/provider_clients.py"))


@pytest.mark.parametrize("as_json", [False, True])
async def test_existing_callable_drives_navigation_and_shared_usage(index, as_json):
    span = index.search("30 days").items[0].span_ids[0]
    actions = iter([{"action": "read", "ids": [span]}, {"action": "stop"}])

    async def existing_application(request):
        assert request.max_output_tokens == 64 and request.timeout_seconds > 0
        assert "action" in request.response_schema["properties"]
        content = next(actions)
        return ModelResponse(json.dumps(content) if as_json else content, 10, 5)

    provider = CallableProvider(existing_application, name="project-model", max_output_tokens=64)
    result = await Navigator(index, policy="model", provider=provider).retrieve("token lifetime")
    assert result.stop_reason == "completed" and result.evidence
    assert result.usage.model_calls == 2 and result.usage.model_tokens == 30
    assert result.usage.reserved_tokens == 0
    assert result.usage.token_accounting == "measured"
    assert index.store.run(result.run_id) == result


@pytest.mark.parametrize("wire_format", ["openai", "anthropic"])
async def test_application_sdk_examples_use_distinct_request_and_response_formats(wire_format):
    class ExistingClient:
        def __init__(self):
            self.responses = self.messages = self

        def with_options(self, **options):
            assert options["max_retries"] == 0 and options["timeout"] > 0
            return self

        async def create(self, **body):
            assert body["model"] == "application-chosen-model"
            if wire_format == "openai":
                assert body["max_output_tokens"] == 512 and body["store"] is False
                assert json.loads(body["input"]) == {"query": "test"}
                assert "system" not in body and "messages" not in body
                return SimpleNamespace(
                    status="completed",
                    output_text='{"action":"stop"}',
                    usage=SimpleNamespace(input_tokens=20, output_tokens=10),
                )
            assert body["max_tokens"] == 512
            assert json.loads(body["messages"][0]["content"]) == {"query": "test"}
            assert "input" not in body and "instructions" not in body
            return SimpleNamespace(
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text='{"action":"stop"}')],
                usage=SimpleNamespace(
                    input_tokens=15,
                    output_tokens=10,
                    cache_read_input_tokens=5,
                    cache_creation_input_tokens=None,
                ),
            )

    factory = CLIENTS["openai_responses" if wire_format == "openai" else "anthropic_messages"]
    provider = factory(ExistingClient(), model="application-chosen-model", cache_key="config-1")
    budget = Budget()
    assert (await provider.action({"query": "test"}, budget)).action == "stop"
    assert budget.usage.model_tokens == 30 and budget.usage.model_calls == 1


async def test_enrichment_cache_separates_application_configurations_without_a_url(index):
    def configured(summary, version):
        async def complete(request):
            return ModelResponse({"summary": summary}, 10, 5)

        return CallableProvider(complete, name="same-project", cache_key=version)

    await enrich(
        index, configured("First configuration", "config-1"), Budget(Limits(model_calls=1000))
    )
    await enrich(
        index, configured("Second configuration", "config-2"), Budget(Limits(model_calls=1000))
    )
    assert all(node.summary == "Second configuration" for node in index.store.load().nodes.values())


async def test_callback_unknown_usage_and_preflight_budget_refusal():
    calls = []

    async def complete(request):
        calls.append(request)
        return ModelResponse({"action": "stop"})

    provider = CallableProvider(complete, name="custom", estimate_input_tokens=lambda request: 20)
    budget = Budget(Limits(model_calls=1, model_tokens=40))
    await provider.action({}, budget)
    assert calls[0].max_output_tokens == 20
    assert budget.usage.model_tokens == 40 and budget.usage.token_accounting == "estimated"
    assert budget.usage.reserved_tokens == 0
    with pytest.raises(BudgetExceeded):
        await provider.action({}, budget)
    with pytest.raises(NavconrError, match="hard total-token"):
        await provider.action({}, Budget(Limits(hard_model_tokens=True)))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "input_tokens,output_tokens,expected",
    [
        (None, None, 30),
        (5, None, 15),
        (None, 7, 27),
        (5, 7, 12),
    ],
)
async def test_partial_sdk_usage_keeps_reported_counts_and_estimates_missing_counts(
    input_tokens, output_tokens, expected
):
    async def complete(request):
        return ModelResponse({"action": "stop"}, input_tokens, output_tokens)

    provider = CallableProvider(
        complete,
        name="partial-usage",
        max_output_tokens=10,
        estimate_input_tokens=lambda request: 20,
    )
    budget = Budget(Limits(model_tokens=100))
    await provider.action({}, budget)
    assert budget.usage.model_tokens == expected
    measured = input_tokens is not None and output_tokens is not None
    assert budget.usage.token_accounting == ("measured" if measured else "estimated")
    assert budget.usage.reserved_tokens == 0


async def test_partial_usage_cannot_hide_a_known_token_overrun():
    async def complete(request):
        return ModelResponse({"action": "stop"}, None, 200)

    provider = CallableProvider(
        complete,
        name="partial-usage",
        max_output_tokens=10,
        estimate_input_tokens=lambda request: 20,
    )
    budget = Budget(Limits(model_tokens=100))
    with pytest.raises(BudgetExceeded):
        await provider.action({}, budget)
    assert budget.usage.model_tokens == 220 and budget.usage.reserved_tokens == 0


@pytest.mark.parametrize("failure", ["error", "invalid", "over_cap"])
async def test_callback_failures_are_charged_without_retries_or_secret_output(failure):
    calls = 0

    async def complete(request):
        nonlocal calls
        calls += 1
        if failure == "error":
            raise RuntimeError("credential-bearing SDK error")
        return ModelResponse(
            "not JSON" if failure == "invalid" else {}, 10, 100 if failure == "over_cap" else 5
        )

    budget = Budget(Limits(retries=5))
    provider = CallableProvider(complete, name="custom", max_output_tokens=50)
    with pytest.raises(NavconrError) as error:
        await provider.action({}, budget)
    assert "credential-bearing" not in str(error.value)
    assert calls == budget.usage.model_calls == 1
    assert budget.usage.model_tokens > 0 and budget.usage.reserved_tokens == 0


async def test_callback_cancellation_and_deadline_settle_the_ledger():
    started = asyncio.Event()

    async def slow(request):
        started.set()
        await asyncio.sleep(30)
        return ModelResponse({"action": "stop"})

    provider = CallableProvider(slow, name="custom")
    budget = Budget()
    task = asyncio.create_task(provider.action({}, budget))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert budget.usage.model_calls == 1 and budget.usage.reserved_tokens == 0
    deadline = Budget(Limits(seconds=0.02))
    with pytest.raises((DeadlineExceeded, TimeoutError)):
        await provider.action({}, deadline)
    assert deadline.usage.model_calls == 1 and deadline.usage.reserved_tokens == 0


def test_cli_loads_existing_project_factory_without_model_or_endpoint(index, monkeypatch, capsys):
    span = index.search("30 days").items[0].span_ids[0]

    def create_provider():
        actions = iter([{"action": "read", "ids": [span]}, {"action": "stop"}])

        async def complete(request):
            return ModelResponse(next(actions), 10, 5)

        return CallableProvider(complete, name="existing-project")

    project = ModuleType("existing_project")
    project.create_provider = create_provider
    monkeypatch.setitem(sys.modules, "existing_project", project)
    assert (
        cli(
            [
                "query",
                "token lifetime",
                "--db",
                str(index.store.path),
                "--policy",
                "model",
                "--provider-factory",
                "existing_project:create_provider",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["evidence"] and result["usage"]["model_calls"] == 2
    assert (
        cli(
            [
                "query",
                "tokens",
                "--db",
                str(index.store.path),
                "--policy",
                "model",
                "--provider-factory",
                "missing_project:create_provider",
            ]
        )
        == 2
    )
    assert "provider factory" in capsys.readouterr().err


def test_paid_smoke_defaults_to_haiku_without_running_it():
    options = runpy.run_path(str(ROOT / "scripts/smoke_anthropic.py"))["options"]
    assert options([]).model == "claude-haiku-5-5"
    assert options(["--model", "claude-opus-5-5"]).model == "claude-opus-5-5"


def test_cli_enrichment_and_evaluation_accept_a_url_free_factory(
    index, tmp_path, monkeypatch, capsys
):
    class ProjectProvider:
        name = "project-owned-reader"

        async def structured(self, prompt, schema, budget):
            budget.charge(model_calls=1)
            if "summary" in schema.model_fields:
                return schema(summary="Application generated hint")
            return schema(text="30 days", span_ids=[prompt["evidence"][0]["span_id"]])

    project = ModuleType("project_models")
    project.configure = ProjectProvider
    monkeypatch.setitem(sys.modules, "project_models", project)
    assert (
        cli(
            [
                "enrich",
                "--db",
                str(index.store.path),
                "--provider-factory",
                "project_models:configure",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["nodes_enriched"] > 0
    dataset = tmp_path / "questions.json"
    dataset.write_text(
        json.dumps(
            {
                "provenance": "offline fixture",
                "review_status": "test",
                "questions": [
                    {
                        "id": "reader",
                        "query": "refresh tokens 30 days",
                        "family": "a",
                        "split": "dev",
                        "category": "lookup",
                        "evidence_groups": [],
                    }
                ],
            }
        )
    )
    assert (
        cli(
            [
                "evaluate",
                str(dataset),
                "--db",
                str(index.store.path),
                "--reader-provider-factory",
                "project_models:configure",
                "--budgets",
                "512",
                "--output",
                str(tmp_path / "results"),
            ]
        )
        == 0
    )
    run = json.loads(capsys.readouterr().out)
    manifest = json.loads((Path(run["path"]) / "manifest.json").read_text())
    assert manifest["reader"]["name"] == "project-owned-reader"
