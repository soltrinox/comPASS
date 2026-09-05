"""Budget envelopes (session / project / org / request).

Tier 3 enforcement:
- ``limit`` / ``spent`` — scoped spend ceiling; λ ramps as utilization rises.
- ``request_ceiling`` / ``estimated_request_cost`` — optional per-request cap.
- When a ceiling is **exceeded**, Route does **not** hard-fail the caller.

**Exceeded policy (documented choice):** ``clamp_to_cheapest`` — select the
lowest-``cost`` candidate still in the allowed set; if none are usable, fall
back to the configured Route default (fail-open). Alternative
``configured_default`` skips straight to the RouteConfig default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


# Documented fail-open policies when spend ceiling is exceeded.
EXCEEDED_CLAMP_TO_CHEAPEST = "clamp_to_cheapest"
EXCEEDED_CONFIGURED_DEFAULT = "configured_default"
_VALID_EXCEEDED = frozenset({EXCEEDED_CLAMP_TO_CHEAPEST, EXCEEDED_CONFIGURED_DEFAULT})


@dataclass
class BudgetEnvelope:
    """Spend envelope with λ ramp and optional request ceiling.

    ``lambda_cost`` is the base cost weight used by Route scoring
    (score = quality − λ · cost). As ``spent/limit`` approaches 1.0, λ is
    raised smoothly so degradation is gradual rather than a cliff.
    """

    scope: str  # session | project | org | request
    limit: float
    spent: float = 0.0
    period: str = "session"
    lambda_cost: float = 1.0
    # Per-request spend ceiling (optional). Compared to estimated_request_cost.
    request_ceiling: float | None = None
    estimated_request_cost: float | None = None
    # Multiplier applied at full utilization (spent == limit).
    # λ_eff = λ * (1 + (m-1)*u^2).
    ramp_multiplier: float = 4.0
    # See module docstring — default is clamp_to_cheapest.
    exceeded_policy: str = EXCEEDED_CLAMP_TO_CHEAPEST

    def __post_init__(self) -> None:
        if self.exceeded_policy not in _VALID_EXCEEDED:
            self.exceeded_policy = EXCEEDED_CLAMP_TO_CHEAPEST

    def utilization(self) -> float:
        """Return spent/limit clamped to [0, 1]. Zero when limit <= 0 (unlimited)."""
        if self.limit <= 0:
            return 0.0
        return max(0.0, min(1.0, float(self.spent) / float(self.limit)))

    def session_exceeded(self) -> bool:
        """True when scoped spend has met or passed the period limit."""
        if self.limit <= 0:
            return False
        return float(self.spent) >= float(self.limit)

    def request_exceeded(self) -> bool:
        """True when estimated request cost exceeds the per-request ceiling."""
        if self.request_ceiling is None or self.estimated_request_cost is None:
            return False
        if self.request_ceiling < 0:
            return False
        return float(self.estimated_request_cost) > float(self.request_ceiling)

    def is_exceeded(self) -> bool:
        """True when session/project/org limit or per-request ceiling is breached."""
        return self.session_exceeded() or self.request_exceeded()

    def effective_lambda(self, base_lambda: float | None = None) -> float:
        """Return λ for scoring, ramping up as utilization approaches 1.0.

        Floor is ``max(lambda_cost, base_lambda or lambda_cost)``. At full
        utilization, λ reaches ``floor * ramp_multiplier``. The curve is
        quadratic in utilization so early spend barely moves λ.
        """
        floor = float(self.lambda_cost)
        if base_lambda is not None:
            floor = max(floor, float(base_lambda))
        u = self.utilization()
        # Soft bump when request ceiling is nearly / already exceeded.
        if self.request_exceeded():
            u = 1.0
        elif (
            self.request_ceiling is not None
            and self.estimated_request_cost is not None
            and self.request_ceiling > 0
        ):
            ru = float(self.estimated_request_cost) / float(self.request_ceiling)
            u = max(u, max(0.0, min(1.0, ru)))
        mult = 1.0 + (max(1.0, float(self.ramp_multiplier)) - 1.0) * (u * u)
        return floor * mult

    def lambda_multiplier(self, base_lambda: float) -> float:
        """Compatibility shim from C1. Prefer ``effective_lambda()``."""
        return self.effective_lambda(base_lambda)

    def cheapest_candidate_id(
        self,
        candidates: Iterable[dict[str, Any]],
        *,
        default_cost: float = 1.0,
    ) -> str | None:
        """Return id of the lowest-cost candidate, or None if none usable."""
        best_id: str | None = None
        best_cost = float("inf")
        for cand in candidates:
            mid = str(cand.get("id") or cand.get("model_version_id") or "")
            if not mid:
                continue
            try:
                cost = float(cand.get("cost", default_cost))
            except (TypeError, ValueError):
                cost = default_cost
            if cost < best_cost:
                best_cost = cost
                best_id = mid
        return best_id

    def resolve_exceeded_selection(
        self,
        candidates: Iterable[dict[str, Any]],
        *,
        default_model_version_id: str,
        default_cost: float = 1.0,
    ) -> tuple[str, str]:
        """Apply exceeded policy → (selected_id, constraint_tag).

        Choice documented at module top: default ``clamp_to_cheapest``.
        """
        if self.exceeded_policy == EXCEEDED_CONFIGURED_DEFAULT:
            return default_model_version_id, "envelope:exceeded:configured_default"
        cheap = self.cheapest_candidate_id(candidates, default_cost=default_cost)
        if cheap is None:
            return default_model_version_id, "envelope:exceeded:configured_default"
        return cheap, "envelope:exceeded:clamp_to_cheapest"

    def record_spend(self, amount: float) -> None:
        """Add realized spend toward the scoped ceiling (mutates in place)."""
        self.spent = float(self.spent) + float(amount)
