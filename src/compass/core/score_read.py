"""Read-only scoring from snapshot / posterior (no file I/O, no keys)."""

from __future__ import annotations

from typing import Any

from compass.core.defaults import DEFAULT_COST, DEFAULT_QUALITY
from compass.score.bandit import BanditPosterior, score as bandit_score


def score_candidates(
    candidates: list[dict[str, Any]],
    *,
    task_class_id: str,
    lambda_cost: float,
    posterior: BanditPosterior | None = None,
    default_quality: float = DEFAULT_QUALITY,
    default_cost: float = DEFAULT_COST,
) -> dict[str, float]:
    """Compute score(m,c) = E[quality] − λ · E[cost] for each candidate id."""
    bandit = posterior or BanditPosterior()
    scores: dict[str, float] = {}
    for cand in candidates:
        mid = str(cand.get("id") or cand.get("model_version_id") or "")
        if not mid:
            continue
        arm = bandit.get_arm(task_class_id, mid)
        if "quality" in cand:
            quality = float(cand["quality"])
        elif arm.pulls > 0:
            quality = float(bandit.expected_quality(arm))
        else:
            quality = float(default_quality)
        if "cost" in cand:
            cost = float(cand["cost"])
        elif arm.cost_mean:
            cost = float(arm.cost_mean)
        else:
            cost = float(default_cost)
        scores[mid] = bandit_score(quality, cost, lambda_cost)
    return scores
