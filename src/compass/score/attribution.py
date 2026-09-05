"""Delayed reward attribution across hops (Track G).

Records joins from late outcomes onto prior RouteDecision nodes via
trajectory_id / episode_id / route_decision_id. Enables later re-scoring.

EXPLICIT NON-CLAIM: multi-hop / multi-agent credit assignment is NOT solved.
Policies below are recording conventions for analysis and optional bandit
updates — not optimality claims.
"""

from __future__ import annotations

import logging
import os
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from compass.graph import GraphStore
    from compass.schema.loader import GraphDocument
    from compass.score.bandit import BanditPosterior

logger = logging.getLogger(__name__)

AttributionPolicyName = Literal["trajectory", "episode", "counterfactual_later"]

# Feature flag: optional bandit posterior update from joined rewards.
# Default OFF — reversible via bitemporal supersede; never implied optimal.
ENV_BANDIT_UPDATE = "COMPASS_ATTRIBUTION_BANDIT_UPDATE"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bandit_update_enabled(*, override: bool | None = None) -> bool:
    """Return whether joined rewards may update bandit posteriors.

    Default false. Override wins when not None; else env
    COMPASS_ATTRIBUTION_BANDIT_UPDATE in {1,true,yes,on}.
    """
    if override is not None:
        return bool(override)
    raw = (os.environ.get(ENV_BANDIT_UPDATE) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass
class DelayedReward:
    """Outcome arriving after one or more RouteDecision hops.

    Join keys (at least one required for a successful join):
      - trajectory_id — multi-hop chain
      - episode_id — short episode / oracle grouping
      - route_decision_id — direct attach to one decision
    Missing all join keys ⇒ fail-open skip (never block Route).
    """

    value: float
    source: str = "verifiable"
    trajectory_id: str | None = None
    episode_id: str | None = None
    route_decision_id: str | None = None
    task_class_id: str | None = None
    observed_at: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def has_join_key(self) -> bool:
        return bool(
            self.trajectory_id or self.episode_id or self.route_decision_id
        )


@dataclass
class AttributionTarget:
    """One RouteDecision selected for attribution recording."""

    route_decision_id: str
    hop_index: int | None
    model_version_id: str | None
    task_class_id: str | None
    share: float = 1.0


@dataclass
class AttributionResult:
    """Outcome of a delayed-reward join attempt."""

    status: Literal["joined", "skipped", "orphaned", "stubbed"]
    policy: AttributionPolicyName
    reward_id: str
    targets: list[AttributionTarget] = field(default_factory=list)
    superseded_ids: list[str] = field(default_factory=list)
    new_decision_ids: list[str] = field(default_factory=list)
    reason: str = ""
    bandit_updated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "policy": self.policy,
            "reward_id": self.reward_id,
            "targets": [
                {
                    "route_decision_id": t.route_decision_id,
                    "hop_index": t.hop_index,
                    "model_version_id": t.model_version_id,
                    "task_class_id": t.task_class_id,
                    "share": t.share,
                }
                for t in self.targets
            ],
            "superseded_ids": list(self.superseded_ids),
            "new_decision_ids": list(self.new_decision_ids),
            "reason": self.reason,
            "bandit_updated": self.bandit_updated,
            "credit_assignment_solved": False,
        }


def select_targets(
    decisions: list[dict[str, Any]],
    reward: DelayedReward,
    policy: AttributionPolicyName,
) -> list[AttributionTarget]:
    """Choose which RouteDecision nodes receive the delayed reward under ``policy``.

    trajectory — all hops sharing trajectory_id (equal recorded share).
    episode — hops sharing episode_id; oracle convention attributes full
              value to the highest hop_index (terminal), others share=0
              but still get a join record for audit.
    counterfactual_later — empty (stub; no write).
    """
    if policy == "counterfactual_later":
        return []

    if not decisions:
        return []

    def _attrs(n: dict[str, Any]) -> dict[str, Any]:
        a = n.get("attrs")
        return a if isinstance(a, dict) else {}

    def _hop(n: dict[str, Any]) -> int:
        h = _attrs(n).get("hop_index")
        try:
            return int(h) if h is not None else -1
        except (TypeError, ValueError):
            return -1

    ordered = sorted(decisions, key=_hop)

    if policy == "episode":
        terminal = ordered[-1]
        targets: list[AttributionTarget] = []
        for n in ordered:
            attrs = _attrs(n)
            is_term = n.get("id") == terminal.get("id")
            targets.append(
                AttributionTarget(
                    route_decision_id=str(n["id"]),
                    hop_index=attrs.get("hop_index"),
                    model_version_id=attrs.get("selected_model_version_id"),
                    task_class_id=attrs.get("task_class_id") or reward.task_class_id,
                    share=1.0 if is_term else 0.0,
                )
            )
        return targets

    # trajectory (default): equal share across hops for recording
    n = len(ordered)
    share = 1.0 / n if n else 1.0
    return [
        AttributionTarget(
            route_decision_id=str(node["id"]),
            hop_index=_attrs(node).get("hop_index"),
            model_version_id=_attrs(node).get("selected_model_version_id"),
            task_class_id=_attrs(node).get("task_class_id") or reward.task_class_id,
            share=share,
        )
        for node in ordered
    ]


def find_joinable_decisions(
    doc: "GraphDocument",
    reward: DelayedReward,
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Locate RouteDecision nodes matching the reward's join keys.

    Precedence: route_decision_id (exact) > trajectory_id > episode_id.
    Fail-open: returns [] when nothing matches.
    """
    nodes = doc.active_nodes(kind="RouteDecision") if active_only else [
        n for n in doc.nodes if n.get("kind") == "RouteDecision"
    ]

    if reward.route_decision_id:
        hit = [n for n in nodes if n.get("id") == reward.route_decision_id]
        if hit:
            return hit
        mirrored = [
            n
            for n in nodes
            if isinstance(n.get("attrs"), dict)
            and n["attrs"].get("route_decision_id") == reward.route_decision_id
        ]
        return mirrored

    if reward.trajectory_id:
        return [
            n
            for n in nodes
            if isinstance(n.get("attrs"), dict)
            and n["attrs"].get("trajectory_id") == reward.trajectory_id
        ]

    if reward.episode_id:
        return [
            n
            for n in nodes
            if isinstance(n.get("attrs"), dict)
            and n["attrs"].get("episode_id") == reward.episode_id
        ]

    return []


def _attributed_attrs(
    old_attrs: dict[str, Any],
    *,
    reward: DelayedReward,
    reward_id: str,
    policy: AttributionPolicyName,
    target: AttributionTarget,
    at: str,
) -> dict[str, Any]:
    attrs = deepcopy(old_attrs) if old_attrs else {}
    attrs["attributed_reward"] = float(reward.value) * float(target.share)
    attrs["attributed_reward_raw"] = float(reward.value)
    attrs["attribution_share"] = float(target.share)
    attrs["attribution_policy"] = policy
    attrs["attribution_reward_id"] = reward_id
    attrs["attribution_source"] = reward.source
    attrs["attribution_at"] = at
    attrs["credit_assignment_solved"] = False
    if reward.trajectory_id and "trajectory_id" not in attrs:
        attrs["trajectory_id"] = reward.trajectory_id
    if reward.episode_id and "episode_id" not in attrs:
        attrs["episode_id"] = reward.episode_id
    prior = attrs.get("attribution_history")
    history = list(prior) if isinstance(prior, list) else []
    history.append(
        {
            "reward_id": reward_id,
            "value": float(reward.value),
            "share": float(target.share),
            "policy": policy,
            "at": at,
        }
    )
    attrs["attribution_history"] = history
    return attrs


def apply_attribution_to_document(
    doc: "GraphDocument",
    reward: DelayedReward,
    *,
    policy: AttributionPolicyName = "trajectory",
    at: str | None = None,
    reward_id: str | None = None,
) -> AttributionResult:
    """Join ``reward`` onto matching RouteDecisions via bitemporal supersede.

    Never raises for orphan/missing ids — returns skipped/orphaned status.
    Does not touch the Route ``decide()`` hot path.
    """
    rid = reward_id or f"urn:mg:reward:{uuid.uuid4().hex[:12]}"
    stamp = at or reward.observed_at or _now_iso()

    if policy == "counterfactual_later":
        return AttributionResult(
            status="stubbed",
            policy=policy,
            reward_id=rid,
            reason=(
                "counterfactual_later is a stub hook only; no graph write. "
                "Credit assignment across hops is not solved."
            ),
        )

    if not reward.has_join_key():
        logger.info("attribution skip: no join keys on delayed reward")
        return AttributionResult(
            status="skipped",
            policy=policy,
            reward_id=rid,
            reason="missing_join_keys",
        )

    decisions = find_joinable_decisions(doc, reward, active_only=True)
    if not decisions:
        logger.info(
            "attribution orphan: no RouteDecision for keys traj=%s ep=%s rd=%s",
            reward.trajectory_id,
            reward.episode_id,
            reward.route_decision_id,
        )
        return AttributionResult(
            status="orphaned",
            policy=policy,
            reward_id=rid,
            reason="no_matching_route_decision",
        )

    targets = select_targets(decisions, reward, policy)
    if not targets:
        return AttributionResult(
            status="skipped",
            policy=policy,
            reward_id=rid,
            reason="policy_selected_no_targets",
        )

    superseded: list[str] = []
    new_ids: list[str] = []
    for target in targets:
        old = doc.node_by_id(target.route_decision_id)
        if old is None:
            continue
        old_attrs = old.get("attrs") if isinstance(old.get("attrs"), dict) else {}
        new_id = f"{target.route_decision_id}:attr:{rid[-8:]}"
        suffix = 0
        candidate = new_id
        while doc.node_by_id(candidate) is not None:
            suffix += 1
            candidate = f"{new_id}:{suffix}"
        new_id = candidate
        new_node = {
            "id": new_id,
            "kind": "RouteDecision",
            "attrs": _attributed_attrs(
                old_attrs,
                reward=reward,
                reward_id=rid,
                policy=policy,
                target=target,
                at=stamp,
            ),
        }
        if old.get("label") is not None:
            new_node["label"] = old.get("label")
        try:
            doc.supersede(
                target.route_decision_id,
                new_node,
                at=stamp,
                reason=f"reward_attribution:{policy}",
            )
        except Exception:  # noqa: BLE001 — fail-open write path
            logger.exception(
                "attribution supersede failed for %s", target.route_decision_id
            )
            continue
        superseded.append(target.route_decision_id)
        new_ids.append(new_id)

    if not new_ids:
        return AttributionResult(
            status="orphaned",
            policy=policy,
            reward_id=rid,
            targets=targets,
            reason="supersede_failed",
        )

    return AttributionResult(
        status="joined",
        policy=policy,
        reward_id=rid,
        targets=targets,
        superseded_ids=superseded,
        new_decision_ids=new_ids,
        reason="ok",
    )


def maybe_update_bandit(
    posterior: "BanditPosterior",
    result: AttributionResult,
    reward: DelayedReward,
    *,
    enabled: bool | None = None,
) -> bool:
    """Optionally update bandit arms from joined targets.

    Gated by feature flag / override. Does not claim optimality.
    Returns True if any arm was updated.
    """
    if not bandit_update_enabled(override=enabled):
        return False
    if result.status != "joined":
        return False
    updated = False
    for t in result.targets:
        if t.share <= 0 or not t.model_version_id:
            continue
        task = t.task_class_id or reward.task_class_id or "default"
        try:
            posterior.update(
                task,
                str(t.model_version_id),
                reward=float(reward.value) * float(t.share),
            )
            updated = True
        except Exception:  # noqa: BLE001
            logger.exception("bandit update from attribution failed")
    return updated


def attach_delayed_reward(
    store: "GraphStore",
    reward: DelayedReward,
    *,
    policy: AttributionPolicyName = "trajectory",
    at: str | None = None,
    posterior: "BanditPosterior | None" = None,
    update_bandit: bool | None = None,
) -> AttributionResult:
    """Persist delayed-reward join onto the graph store (async / post-hoc API).

    Fail-open: load/save errors become skipped/orphaned results, never raised
    into a Route caller. Must not be invoked from ``decide()``.
    """
    try:
        doc = store.load_document(fail_open=True)
        result = apply_attribution_to_document(
            doc, reward, policy=policy, at=at
        )
        if result.status == "joined":
            store.save_document(doc)
            if posterior is not None:
                result.bandit_updated = maybe_update_bandit(
                    posterior, result, reward, enabled=update_bandit
                )
                if result.bandit_updated and hasattr(store, "config"):
                    try:
                        bandit_path = store.config.bandit_path
                        posterior.save(bandit_path)
                    except Exception:  # noqa: BLE001
                        logger.exception("bandit save after attribution failed")
        return result
    except Exception as exc:  # noqa: BLE001 — never block callers
        logger.exception("attach_delayed_reward failed")
        return AttributionResult(
            status="skipped",
            policy=policy,
            reward_id="urn:mg:reward:error",
            reason=f"exception:{type(exc).__name__}",
        )


# Public alias matching plan language
join_delayed_reward = attach_delayed_reward
