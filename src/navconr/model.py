"""Provider-neutral model contracts. No HTTP payloads, SDKs, or credentials."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .budget import Budget
from .models import Action, BudgetExceeded, DeadlineExceeded, NavconrError
from .util import identity

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class StructuredProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def structured(
        self, prompt: dict, schema: type[ResponseModel], budget: Budget
    ) -> ResponseModel: ...


class PolicyProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def action(self, prompt: dict, budget: Budget) -> Action: ...


def provider_cache_key(provider: StructuredProvider) -> str:
    """An opaque configuration identity, independent of endpoint/request format.

    Custom providers can expose cache_key; otherwise their name must distinguish
    model, prompt version and relevant configuration. Never include credentials.
    """
    key = getattr(provider, "cache_key", provider.name)
    if not isinstance(key, str) or not key:
        raise NavconrError("provider cache identity must be a nonempty string")
    return identity("provider-1", key)


@dataclass(frozen=True)
class ModelRequest:
    prompt: dict
    response_schema: dict
    max_output_tokens: int
    timeout_seconds: float


@dataclass(frozen=True)
class ModelResponse:
    content: str | dict
    input_tokens: int | None = None
    output_tokens: int | None = None


class CallableProvider:
    """Use an application-owned async model call with Navconr's budget ledger.

    The callback owns SDK/wire serialization and response extraction. It must
    honor the supplied output cap/deadline and disable hidden SDK retries.
    Report total usage including cached input and reasoning/output tokens.
    Unknown usage is conservatively estimated; hard token guarantees fail closed.
    """

    def __init__(
        self,
        complete: Callable[[ModelRequest], Awaitable[ModelResponse]],
        *,
        name: str,
        cache_key: str | None = None,
        max_output_tokens: int = 512,
        estimate_input_tokens: Callable[[ModelRequest], int] | None = None,
    ):
        if not name.strip() or max_output_tokens < 1 or cache_key == "":
            raise NavconrError("a provider name and positive output cap are required")
        self.name, self.cache_key = name, cache_key if cache_key is not None else name
        self.complete, self.max_output_tokens = complete, max_output_tokens
        self.estimate_input_tokens = estimate_input_tokens

    async def structured(
        self, prompt: dict, schema: type[ResponseModel], budget: Budget
    ) -> ResponseModel:
        if budget.limits.hard_model_tokens:
            raise NavconrError("callable provider cannot guarantee a hard total-token cap")
        budget.check()
        request = ModelRequest(
            prompt=deepcopy(prompt),
            response_schema=schema.model_json_schema(),
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=budget.remaining_seconds,
        )
        estimated_input = (
            self.estimate_input_tokens(request)
            if self.estimate_input_tokens
            else len(json.dumps([request.prompt, request.response_schema]).encode()) + 512
        )
        if type(estimated_input) is not int or estimated_input < 0:
            raise NavconrError("input token estimate must be a nonnegative integer")
        available = (
            budget.limits.model_tokens - budget.usage.model_tokens - budget.usage.reserved_tokens
        )
        output_cap = min(self.max_output_tokens, available - estimated_input)
        if output_cap < 1:
            raise BudgetExceeded("insufficient model token reservation")
        request = replace(request, max_output_tokens=output_cap)
        reserved = estimated_input + output_cap
        budget.reserve_model(reserved)
        settled = False
        try:
            async with asyncio.timeout(budget.remaining_seconds):
                response = await self.complete(request)
            if not isinstance(response, ModelResponse):
                raise ValueError("callback must return ModelResponse")
            counts = (response.input_tokens, response.output_tokens)
            if any(value is not None and (type(value) is not int or value < 0) for value in counts):
                raise ValueError("invalid model usage")
            measured = all(value is not None for value in counts)
            actual = (
                response.input_tokens if response.input_tokens is not None else estimated_input
            ) + (response.output_tokens if response.output_tokens is not None else output_cap)
            settled = True
            budget.reconcile_model(reserved, actual, measured)
            if response.output_tokens is not None and response.output_tokens > output_cap:
                raise NavconrError("model callback exceeded the requested output cap")
            return (
                schema.model_validate_json(response.content)
                if isinstance(response.content, str)
                else schema.model_validate(response.content)
            )
        except (BudgetExceeded, DeadlineExceeded, TimeoutError, asyncio.CancelledError):
            raise
        except Exception:
            # SDK exceptions can contain headers, payloads, or credential-bearing URLs.
            raise NavconrError(
                "model callback failed or returned invalid structured output"
            ) from None
        finally:
            if not settled:
                budget.reconcile_model(reserved, reserved, measured=False)

    async def action(self, prompt: dict, budget: Budget) -> Action:
        return await self.structured(prompt, Action, budget)
