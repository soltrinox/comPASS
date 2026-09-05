"""Bandit posterior over (TaskClass, ModelVersion) arms with JSON persistence.

Default allocator: Thompson sampling. UCB available as fallback via config.
Routing uses score = E[quality] - lambda * E[cost] (not a constrained optimizer).
C2: real update + save/load (not stubs); fail-open defaults when empty/corrupt.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Allocator = Literal["thompson", "ucb"]

POSTERIOR_SCHEMA = "compass-bandit-posterior/v1"


@dataclass
class BanditConfig:
    """Bandit runtime knobs."""

    allocator: Allocator = "thompson"
    lambda_cost: float = 1.0
    ucb_c: float = 1.0
    default_quality: float = 0.5
    default_cost: float = 1.0
    seed: int | None = None


@dataclass
class BanditArm:
    """One (TaskClass, ModelVersion) arm with Beta-Bernoulli quality prior."""

    task_class_id: str
    model_version_id: str
    alpha: float = 1.0  # successes + 1
    beta: float = 1.0  # failures + 1
    cost_mean: float = 1.0
    pulls: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_class_id": self.task_class_id,
            "model_version_id": self.model_version_id,
            "alpha": self.alpha,
            "beta": self.beta,
            "cost_mean": self.cost_mean,
            "pulls": self.pulls,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BanditArm:
        return cls(
            task_class_id=str(data["task_class_id"]),
            model_version_id=str(data["model_version_id"]),
            alpha=float(data.get("alpha", 1.0)),
            beta=float(data.get("beta", 1.0)),
            cost_mean=float(data.get("cost_mean", 1.0)),
            pulls=int(data.get("pulls", 0)),
        )


@dataclass
class BanditPosterior:
    """Posterior table with optional JSON persistence. Fail-open when empty."""

    arms: dict[tuple[str, str], BanditArm] = field(default_factory=dict)
    config: BanditConfig = field(default_factory=BanditConfig)
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.config.seed)

    def get_arm(self, task_class_id: str, model_version_id: str) -> BanditArm:
        key = (task_class_id, model_version_id)
        if key not in self.arms:
            self.arms[key] = BanditArm(
                task_class_id=task_class_id,
                model_version_id=model_version_id,
                cost_mean=self.config.default_cost,
            )
        return self.arms[key]

    def update(
        self,
        task_class_id: str,
        model_version_id: str,
        *,
        reward: float,
        cost: float | None = None,
    ) -> BanditArm:
        """Update Beta posterior from a Bernoulli-ish reward in [0, 1].

        reward >= 0.5 counts as success (alpha += 1); otherwise beta += 1.
        Optional cost updates an exponential moving average of cost_mean.
        """
        arm = self.get_arm(task_class_id, model_version_id)
        r = max(0.0, min(1.0, float(reward)))
        if r >= 0.5:
            arm.alpha += 1.0
        else:
            arm.beta += 1.0
        arm.pulls += 1
        if cost is not None:
            c = float(cost)
            if arm.pulls <= 1:
                arm.cost_mean = c
            else:
                # EMA toward observed cost
                arm.cost_mean = 0.8 * arm.cost_mean + 0.2 * c
        return arm

    def expected_quality(self, arm: BanditArm) -> float:
        total = arm.alpha + arm.beta
        if total <= 0:
            return self.config.default_quality
        return arm.alpha / total

    def sample_quality(self, arm: BanditArm) -> float:
        """Thompson sample from Beta(alpha, beta); fail-open to default."""
        try:
            if arm.alpha <= 0 or arm.beta <= 0:
                return self.config.default_quality
            x = self._rng.gammavariate(arm.alpha, 1.0)
            y = self._rng.gammavariate(arm.beta, 1.0)
            denom = x + y
            if denom <= 0:
                return self.config.default_quality
            return x / denom
        except Exception:
            return self.config.default_quality

    def ucb_score(self, arm: BanditArm, total_pulls: int) -> float:
        q = self.expected_quality(arm)
        if arm.pulls <= 0:
            return float("inf")
        bonus = self.config.ucb_c * math.sqrt(math.log(max(total_pulls, 1) + 1) / arm.pulls)
        return q + bonus

    def allocate(self, task_class_id: str, model_version_ids: list[str]) -> str | None:
        """Choose an arm for probe spend. Empty candidates → None (fail-open)."""
        if not model_version_ids:
            return None
        try:
            arms = [self.get_arm(task_class_id, mid) for mid in model_version_ids]
            if self.config.allocator == "ucb":
                total = sum(a.pulls for a in arms)
                return max(arms, key=lambda a: self.ucb_score(a, total)).model_version_id
            return max(arms, key=self.sample_quality).model_version_id
        except Exception:
            return model_version_ids[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": POSTERIOR_SCHEMA,
            "config": {
                "allocator": self.config.allocator,
                "lambda_cost": self.config.lambda_cost,
                "ucb_c": self.config.ucb_c,
                "default_quality": self.config.default_quality,
                "default_cost": self.config.default_cost,
                "seed": self.config.seed,
            },
            "arms": [arm.to_dict() for arm in self.arms.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, config: BanditConfig | None = None) -> BanditPosterior:
        if not isinstance(data, dict):
            return cls(config=config or BanditConfig())
        cfg_data = data.get("config") if isinstance(data.get("config"), dict) else {}
        cfg = config or BanditConfig(
            allocator=cfg_data.get("allocator", "thompson"),  # type: ignore[arg-type]
            lambda_cost=float(cfg_data.get("lambda_cost", 1.0)),
            ucb_c=float(cfg_data.get("ucb_c", 1.0)),
            default_quality=float(cfg_data.get("default_quality", 0.5)),
            default_cost=float(cfg_data.get("default_cost", 1.0)),
            seed=cfg_data.get("seed"),
        )
        post = cls(config=cfg)
        for raw in data.get("arms") or []:
            if not isinstance(raw, dict):
                continue
            try:
                arm = BanditArm.from_dict(raw)
            except (KeyError, TypeError, ValueError):
                continue
            post.arms[(arm.task_class_id, arm.model_version_id)] = arm
        return post

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2) + chr(10), encoding="utf-8")

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        config: BanditConfig | None = None,
        fail_open: bool = True,
    ) -> BanditPosterior:
        """Load posterior from JSON. Missing/corrupt → empty posterior when fail_open."""
        p = Path(path)
        if not p.exists():
            if fail_open:
                return cls(config=config or BanditConfig())
            raise FileNotFoundError(p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return cls.from_dict(data, config=config)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            if fail_open:
                return cls(config=config or BanditConfig())
            raise


def score(quality: float, cost: float, lambda_cost: float) -> float:
    """Routing score: E[quality] - λ · E[cost]."""
    return float(quality) - float(lambda_cost) * float(cost)
