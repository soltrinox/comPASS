"""Route plane: classify → score → decide (fail-open).

Note: do not re-export the `decide` *function* as `compass.route.decide` —
that name must remain the submodule for `from compass.route.decide import decide`.
"""

from compass.route.classify import classify
from compass.route.decide import RouteConfig, RouteDecisionResult
from compass.route.envelope import (
    EXCEEDED_CLAMP_TO_CHEAPEST,
    EXCEEDED_CONFIGURED_DEFAULT,
    BudgetEnvelope,
)

__all__ = [
    "BudgetEnvelope",
    "EXCEEDED_CLAMP_TO_CHEAPEST",
    "EXCEEDED_CONFIGURED_DEFAULT",
    "RouteConfig",
    "RouteDecisionResult",
    "classify",
]
