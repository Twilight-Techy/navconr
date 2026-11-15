from __future__ import annotations

import threading
import time

from .models import BudgetExceeded, DeadlineExceeded, Limits, Usage


class Budget:
    """One shared ledger per session; concurrent reservations are atomic."""

    def __init__(self, limits: Limits | None = None):
        self.limits = limits or Limits()
        self.usage = Usage()
        self.started = time.monotonic()
        self._lock = threading.RLock()
        self._has_estimated_usage = False

    @property
    def remaining_seconds(self) -> float:
        return max(0, self.limits.seconds - (time.monotonic() - self.started))

    def check(self) -> None:
        if self.remaining_seconds <= 0:
            raise DeadlineExceeded("absolute session deadline exceeded")

    def charge(self, **amounts: int) -> None:
        with self._lock:
            self.check()
            for name, amount in amounts.items():
                if amount < 0:
                    raise ValueError("negative budget charge")
                current = getattr(self.usage, name)
                extra = self.usage.reserved_tokens if name == "model_tokens" else 0
                if current + amount + extra > getattr(self.limits, name):
                    raise BudgetExceeded(f"{name} budget exhausted")
            for name, amount in amounts.items():
                setattr(self.usage, name, getattr(self.usage, name) + amount)

    def reserve_model(self, tokens: int) -> None:
        with self._lock:
            self.charge(model_calls=1, model_tokens=tokens)
            self.usage.model_tokens -= tokens
            self.usage.reserved_tokens += tokens

    def reconcile_model(self, reserved: int, actual: int, measured: bool) -> None:
        with self._lock:
            if reserved < 0 or reserved > self.usage.reserved_tokens or actual < 0:
                raise ValueError("invalid model reservation reconciliation")
            self.usage.reserved_tokens -= reserved
            self.usage.model_tokens += actual
            if not measured:
                self._has_estimated_usage = True
            self.usage.token_accounting = "estimated" if self._has_estimated_usage else "measured"
            if self.usage.model_tokens + self.usage.reserved_tokens > self.limits.model_tokens:
                raise BudgetExceeded("provider exceeded reserved token estimate")
            self.check()
