"""Reward sources and delayed-reward recording (Track G).

1. Verifiable outcomes — strongest
2. Implicit compressor signals — weak prior only
3. Model-as-judge — last resort; record judge identity

C1/Track G: recording + join APIs only.
EXPLICIT NON-CLAIM: Do not claim solved credit assignment across hops.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, TYPE_CHECKING

from compass.score.attribution import (
    AttributionPolicyName,
    AttributionResult,
    DelayedReward,
    attach_delayed_reward,
)

if TYPE_CHECKING:
    from compass.graph import GraphStore
    from compass.score.bandit import BanditPosterior

logger = logging.getLogger(__name__)

RewardSource = Literal["verifiable", "implicit", "judge"]


@dataclass
class RewardObservation:
    """A single reward observation, optionally keyed for delayed join."""

    source: RewardSource
    value: float
    task_class_id: str
    model_version_id: str
    meta: dict[str, Any] | None = None
    trajectory_id: str | None = None
    episode_id: str | None = None
    route_decision_id: str | None = None
    hop_index: int | None = None
    observed_at: str = ""


def to_delayed_reward(obs: RewardObservation) -> DelayedReward:
    """Map a RewardObservation into a DelayedReward join payload."""
    meta = dict(obs.meta or {})
    meta.setdefault("model_version_id", obs.model_version_id)
    if obs.hop_index is not None:
        meta.setdefault("hop_index", obs.hop_index)
    return DelayedReward(
        value=float(obs.value),
        source=str(obs.source),
        trajectory_id=obs.trajectory_id,
        episode_id=obs.episode_id,
        route_decision_id=obs.route_decision_id,
        task_class_id=obs.task_class_id,
        observed_at=obs.observed_at,
        meta=meta,
    )


def record_reward(
    obs: RewardObservation,
    *,
    store: GraphStore | None = None,
    policy: AttributionPolicyName = "trajectory",
    posterior: BanditPosterior | None = None,
    update_bandit: bool | None = None,
) -> AttributionResult | None:
    """Persist reward for later / immediate attribution.

    When ``store`` is None this is a no-op stub (C1 compat) returning None.
    When provided, joins onto prior RouteDecisions asynchronously/post-hoc.
    Never raises into Route; join failures become AttributionResult statuses.
    """
    if store is None:
        return None
    delayed = to_delayed_reward(obs)
    return attach_delayed_reward(
        store,
        delayed,
        policy=policy,
        at=obs.observed_at or None,
        posterior=posterior,
        update_bandit=update_bandit,
    )


def attach_reward_to_trajectory(
    store: GraphStore,
    *,
    value: float,
    trajectory_id: str,
    source: RewardSource = "verifiable",
    task_class_id: str | None = None,
    policy: AttributionPolicyName = "trajectory",
    observed_at: str = "",
    posterior: BanditPosterior | None = None,
    update_bandit: bool | None = None,
) -> AttributionResult:
    """API: attach a delayed reward to all RouteDecisions in a trajectory."""
    return attach_delayed_reward(
        store,
        DelayedReward(
            value=value,
            source=source,
            trajectory_id=trajectory_id,
            task_class_id=task_class_id,
            observed_at=observed_at,
        ),
        policy=policy,
        at=observed_at or None,
        posterior=posterior,
        update_bandit=update_bandit,
    )


def attach_reward_to_route_decision(
    store: GraphStore,
    *,
    value: float,
    route_decision_id: str,
    source: RewardSource = "verifiable",
    task_class_id: str | None = None,
    policy: AttributionPolicyName = "trajectory",
    observed_at: str = "",
    posterior: BanditPosterior | None = None,
    update_bandit: bool | None = None,
) -> AttributionResult:
    """API: attach a delayed reward directly to one RouteDecision id."""
    return attach_delayed_reward(
        store,
        DelayedReward(
            value=value,
            source=source,
            route_decision_id=route_decision_id,
            task_class_id=task_class_id,
            observed_at=observed_at,
        ),
        policy=policy,
        at=observed_at or None,
        posterior=posterior,
        update_bandit=update_bandit,
    )
