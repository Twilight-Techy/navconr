import asyncio
import json

import httpx
import pytest

from navconr import Limits
from navconr.anthropic import AnthropicProvider
from navconr.budget import Budget
from navconr.models import BudgetExceeded, NavconrError


def response(text='{"action":"stop"}', stop="end_turn"):
    return httpx.Response(
        200,
        json={
            "content": [
                {"type": "thinking", "thinking": "private content must be discarded"},
                {"type": "text", "text": text},
            ],
            "stop_reason": stop,
            "usage": {"input_tokens": 30, "output_tokens": 15, "cache_read_input_tokens": 5},
        },
    )


async def test_anthropic_schema_caps_usage_and_call_limit():
    requests = []

    def handle(request):
        requests.append(request)
        assert request.url.host == "api.anthropic.com"
        assert request.headers["x-api-key"] == "fixture-only"
        assert request.headers["anthropic-version"] == "2026-10-21"
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 30})
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 160
        assert payload["output_config"] == {"effort": "low"}
        assert payload["service_tier"] == "standard_only"
        assert "fixture-only" not in request.content.decode()
        return response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = AnthropicProvider("fixture", api_key="fixture-only", client=client)
        budget = Budget(Limits(model_calls=1))
        action = await provider.action({"query": "test"}, budget)
        assert action.action == "stop"
        assert budget.usage.model_tokens == 50  # Includes cached input and thinking/output.
        assert budget.usage.token_accounting == "measured"
        assert budget.usage.reserved_tokens == 0
        assert budget.usage.model_calls == 1
        assert "private content" not in json.dumps(provider.last_usage)
        with pytest.raises(BudgetExceeded):
            await provider.action({}, budget)
        assert len(requests) == 2


async def test_anthropic_preflight_refuses_large_input_without_generation():
    paths = []

    def handle(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={"input_tokens": 601})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = AnthropicProvider("fixture", api_key="fixture-only", client=client)
        budget = Budget()
        with pytest.raises(BudgetExceeded, match="preflight"):
            await provider.action({}, budget)
        assert paths == ["/v1/messages/count_tokens"]
        assert budget.usage.model_calls == 0
        with pytest.raises(NavconrError, match="hard total-token"):
            await provider.action({}, Budget(Limits(hard_model_tokens=True)))
        assert len(paths) == 1


@pytest.mark.parametrize("status", [401, 429, 503, 307])
async def test_anthropic_failures_never_retry_or_expose_response(status):
    paths = []

    def handle(request):
        paths.append(request.url.path)
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 20})
        return httpx.Response(
            status, headers={"location": "https://elsewhere.invalid"}, text="secret"
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = AnthropicProvider("fixture", api_key="fixture-only", client=client)
        budget = Budget(Limits(retries=5))
        with pytest.raises(NavconrError, match=f"HTTP {status}") as error:
            await provider.action({}, budget)
        assert "secret" not in str(error.value) and "fixture-only" not in str(error.value)
        assert len(paths) == 2
        assert budget.usage.model_calls == 1 and budget.usage.model_tokens > 0
        assert budget.usage.reserved_tokens == 0


@pytest.mark.parametrize("result", [response("not JSON"), response(stop="max_tokens")])
async def test_anthropic_invalid_or_truncated_output_preserves_measured_usage(result):
    def handle(request):
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 30})
        return result

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = AnthropicProvider("fixture", api_key="fixture-only", client=client)
        budget = Budget()
        with pytest.raises(NavconrError):
            await provider.action({}, budget)
        assert budget.usage.model_calls == 1
        assert budget.usage.model_tokens == 50
        assert budget.usage.reserved_tokens == 0


async def test_anthropic_cancellation_settles_reservation():
    started = asyncio.Event()

    async def handle(request):
        if request.url.path.endswith("count_tokens"):
            return httpx.Response(200, json={"input_tokens": 30})
        started.set()
        await asyncio.sleep(30)
        return response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = AnthropicProvider("fixture", api_key="fixture-only", client=client)
        budget = Budget()
        task = asyncio.create_task(provider.action({}, budget))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert budget.usage.model_calls == 1
        assert budget.usage.model_tokens > 0 and budget.usage.reserved_tokens == 0
