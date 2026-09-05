"""Reward sources for bandit updates (stub).

1. Verifiable outcomes — strongest
2. Implicit compressor signals — weak prior only
3. Model-as-judge — last resort; record judge identity

C1: interface stub only. Do not claim solved credit assignment across hops.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

RewardSource = Literal["verifiable", "implicit", "judge"]


@dataclass
class RewardObservation:
    source: RewardSource
    value: float
    task_class_id: str
    model_version_id: str
    meta: dict[str, Any] | None = None


def record_reward(_obs: RewardObservation) -> None:
    """Persist reward for later attribution (C1 no-op stub)."""
    return None
