"""Scoring plane helpers: bandit allocation, reward, drift, attribution."""

from compass.score.attribution import (
    AttributionResult,
    DelayedReward,
    attach_delayed_reward,
    join_delayed_reward,
)
from compass.score.reward import (
    RewardObservation,
    attach_reward_to_route_decision,
    attach_reward_to_trajectory,
    record_reward,
)

__all__ = [
    "AttributionResult",
    "DelayedReward",
    "RewardObservation",
    "attach_delayed_reward",
    "attach_reward_to_route_decision",
    "attach_reward_to_trajectory",
    "join_delayed_reward",
    "record_reward",
]
