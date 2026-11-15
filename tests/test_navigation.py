import asyncio

import httpx
import pytest

from navconr import Limits
from navconr.budget import Budget
from navconr.models import Action, NavconrError
from navconr.navigation import Navigator
from navconr.providers import OllamaProvider, ScriptedProvider


async def test_local_navigation_and_replay(index):
    result = await Navigator(index).retrieve("refresh tokens revocation")
    assert result.evidence
    assert any("Redis" in item.text for item in result.evidence)
    assert result.stop_reason == "completed"
    replay = index.store.run(result.run_id)
    assert replay == result
    assert [event.sequence for event in replay.trace] == list(range(len(replay.trace)))


async def test_absent_evidence_and_tiny_budget(index):
    absent = await Navigator(index).retrieve("qzxnonexistent")
    assert absent.stop_reason == "insufficient_evidence"
    small = await Navigator(index).retrieve("tokens", limits=Limits(steps=1))
    assert small.stop_reason == "budget_exhausted"


async def test_scripted_model_actions_are_validated(index):
    span = index.search("30 days").items[0].span_ids[0]
    provider = ScriptedProvider([Action(action="read", ids=[span]), Action(action="stop")])
    result = await Navigator(index, policy="model", provider=provider).retrieve("token lifetime")
    assert result.evidence and result.usage.model_calls == 2
    bad = ScriptedProvider([Action(action="expand", ids=["invented"])])
    failure = await Navigator(index, policy="model", provider=bad).retrieve("tokens")
    assert failure.stop_reason == "failed"


async def test_ollama_mock_transport_usage_and_schema():
    def handle(request):
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "message": {"content": '{"action":"stop"}'},
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = OllamaProvider("fixture", client=client)
        budget = Budget()
        action = await provider.action({"query": "test"}, budget)
        assert action.action == "stop"
        assert budget.usage.model_tokens == 15
        assert budget.usage.token_accounting == "measured"
        assert budget.usage.reserved_tokens == 0
        with pytest.raises(NavconrError, match="hard total-token"):
            await provider.action({}, Budget(Limits(hard_model_tokens=True)))


async def test_model_cancellation_is_recorded(index):
    class Slow:
        name = "slow-fixture"

        async def action(self, prompt, budget):
            await asyncio.sleep(30)

    task = asyncio.create_task(Navigator(index, policy="model", provider=Slow()).retrieve("tokens"))
    await asyncio.sleep(0.02)
    task.cancel()
    result = await task
    assert result.stop_reason == "cancelled"


async def test_node_with_many_locations_fetches_every_span(index):
    from navconr.models import Node, Span

    data = index.store.load().model_copy(deep=True)
    source = data.sources["auth.md"]
    span_ids = []
    for position in range(25):
        sid = f"location-{position}"
        data.spans[sid] = Span(
            id=sid, blob=source.blob, source=source.path, start=position, end=position + 1
        )
        span_ids.append(sid)
    data.nodes["many-locations"] = Node(
        id="many-locations",
        kind="block",
        title="Multiple evidence locations",
        parent="root",
        source=source.path,
        span_ids=span_ids,
    )
    data.revision = "multi-location-fixture"
    index.store.publish(data, {})
    result = await Navigator(index).retrieve("multiple evidence locations")
    assert set(span_ids) <= {item.span.id for item in result.evidence}


async def test_failed_provider_attempts_cannot_bypass_call_budget():
    from navconr.models import BudgetExceeded

    calls = 0

    def failed(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(failed)) as client:
        budget = Budget(Limits(model_calls=1, retries=1))
        with pytest.raises(BudgetExceeded):
            await OllamaProvider("fixture", client=client).action({}, budget)
        assert calls == 1
        assert budget.usage.reserved_tokens == 0
        assert budget.usage.model_tokens > 0
