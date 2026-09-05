"""Per-provider rate limits, jittered backoff, and budget caps for Probe fan-out.

Live probe fan-out must stay bounded. Limiters are process-local and injectable
for tests (no real sleeps when ``sleep_fn`` is a no-op).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable

SleepFn = Callable[[float], None]


@dataclass
class RateLimitConfig:
    """Budget and pacing knobs for one provider (or the default profile)."""

    max_concurrent: int = 2
    min_interval_s: float = 0.25
    max_calls_per_minute: int = 30
    budget_cap: int = 100
    backoff_base_s: float = 0.5
    backoff_max_s: float = 30.0
    jitter_s: float = 0.1


class RateLimitExceeded(RuntimeError):
    """Raised when a provider budget or rate cap is exhausted."""


@dataclass
class _ProviderState:
    in_flight: int = 0
    calls_total: int = 0
    window_start: float = 0.0
    window_count: int = 0
    last_call_at: float = 0.0
    consecutive_failures: int = 0


class ProviderRateLimiter:
    """Per-provider limiter with jittered exponential backoff (single-threaded safe)."""

    def __init__(
        self,
        *,
        default: RateLimitConfig | None = None,
        per_provider: dict[str, RateLimitConfig] | None = None,
        sleep_fn: SleepFn | None = None,
        clock: Callable[[], float] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._default = default or RateLimitConfig()
        self._per = dict(per_provider or {})
        self._sleep = sleep_fn or time.sleep
        self._clock = clock or time.monotonic
        self._rng = rng or random.Random()
        self._states: dict[str, _ProviderState] = {}

    def config_for(self, provider: str) -> RateLimitConfig:
        return self._per.get(provider, self._default)

    def _state(self, provider: str) -> _ProviderState:
        st = self._states.get(provider)
        if st is None:
            st = _ProviderState()
            self._states[provider] = st
        return st

    def remaining_budget(self, provider: str) -> int:
        cfg = self.config_for(provider)
        st = self._state(provider)
        return max(0, cfg.budget_cap - st.calls_total)

    def acquire(self, provider: str) -> None:
        """Block (via sleep_fn) until a slot is available; raise on budget exhaust."""
        cfg = self.config_for(provider)
        st = self._state(provider)
        for _ in range(10_000):
            now = self._clock()
            if st.window_start <= 0.0 or (now - st.window_start) >= 60.0:
                st.window_start = now
                st.window_count = 0
            if st.calls_total >= cfg.budget_cap:
                raise RateLimitExceeded(
                    f"provider {provider!r} budget_cap={cfg.budget_cap} exhausted"
                )
            if st.window_count >= cfg.max_calls_per_minute:
                wait = max(0.001, 60.0 - (now - st.window_start)) + self._jitter(cfg)
                self._sleep(wait)
                continue
            if st.in_flight >= cfg.max_concurrent:
                wait = max(cfg.min_interval_s, 0.001) + self._jitter(cfg)
                self._sleep(wait)
                continue
            if st.last_call_at > 0 and (now - st.last_call_at) < cfg.min_interval_s:
                wait = cfg.min_interval_s - (now - st.last_call_at) + self._jitter(cfg)
                self._sleep(max(0.001, wait))
                continue
            st.in_flight += 1
            st.calls_total += 1
            st.window_count += 1
            st.last_call_at = now
            return
        raise RateLimitExceeded(f"provider {provider!r} acquire spun too long")

    def release(self, provider: str, *, success: bool = True) -> None:
        st = self._state(provider)
        st.in_flight = max(0, st.in_flight - 1)
        if success:
            st.consecutive_failures = 0
        else:
            st.consecutive_failures += 1

    def backoff_seconds(self, provider: str) -> float:
        cfg = self.config_for(provider)
        st = self._state(provider)
        n = st.consecutive_failures
        if n <= 0:
            return 0.0
        delay = min(cfg.backoff_max_s, cfg.backoff_base_s * (2 ** (n - 1)))
        return delay + self._jitter(cfg)

    def sleep_backoff(self, provider: str) -> float:
        delay = self.backoff_seconds(provider)
        if delay > 0:
            self._sleep(delay)
        return delay

    def snapshot(self) -> dict[str, dict[str, int | float]]:
        """Proof-friendly counters for test-results logs."""
        out: dict[str, dict[str, int | float]] = {}
        for name, st in self._states.items():
            out[name] = {
                "calls_total": st.calls_total,
                "in_flight": st.in_flight,
                "window_count": st.window_count,
                "consecutive_failures": st.consecutive_failures,
                "remaining_budget": self.remaining_budget(name),
            }
        return out

    def _jitter(self, cfg: RateLimitConfig) -> float:
        if cfg.jitter_s <= 0:
            return 0.0
        return self._rng.uniform(0.0, cfg.jitter_s)


DEFAULT_LIMITER = ProviderRateLimiter()


__all__ = [
    "DEFAULT_LIMITER",
    "ProviderRateLimiter",
    "RateLimitConfig",
    "RateLimitExceeded",
]
