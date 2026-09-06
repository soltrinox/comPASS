"""Fail-open routing decision: classify → score → persist RouteDecision.

score(m, c) = E[quality] − λ · E[cost]
No provider keys in this module or its call graph.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from compass.route.classify import DEFAULT_TASK_CLASS, classify
from compass.route.envelope import BudgetEnvelope
from compass.score.bandit import BanditPosterior, score as bandit_score

if TYPE_CHECKING:
    from compass.graph import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class RouteConfig:
    """Hot-path routing configuration. Never holds provider credentials."""

    default_model_version_id: str = "default"
    lambda_cost: float = 1.0
    default_quality: float = 0.5
    default_cost: float = 1.0


@dataclass
class RouteDecisionResult:
    """Machine-readable routing outcome (logical RouteDecision attrs)."""

    selected_model_version_id: str
    task_class_id: str
    score: float
    lambda_cost: float
    scores: dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    fail_open: bool = False
    default_reason: str | None = None
    decided_at: str = ""
    route_decision_id: str | None = None
    constraints_applied: list[str] = field(default_factory=list)
    trajectory_id: str | None = None
    episode_id: str | None = None
    hop_index: int | None = None
    selection_mode: str | None = None  # decide | catalog | proxy_override

    def to_attrs(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "task_class_id": self.task_class_id,
            "selected_model_version_id": self.selected_model_version_id,
            "scores": dict(self.scores),
            "lambda": self.lambda_cost,
            "constraints_applied": list(self.constraints_applied),
            "rationale": self.rationale,
            "fail_open": self.fail_open,
            "default_reason": self.default_reason,
            "decided_at": self.decided_at,
        }
        if self.trajectory_id is not None:
            attrs["trajectory_id"] = self.trajectory_id
        if self.episode_id is not None:
            attrs["episode_id"] = self.episode_id
        if self.hop_index is not None:
            attrs["hop_index"] = self.hop_index
        if self.selection_mode is not None:
            attrs["selection_mode"] = self.selection_mode
        return attrs


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_envelope(
    envelope: BudgetEnvelope | dict[str, Any] | None,
    config: RouteConfig,
) -> BudgetEnvelope | None:
    if envelope is None:
        return None
    if isinstance(envelope, BudgetEnvelope):
        return envelope
    if isinstance(envelope, dict):
        try:
            return BudgetEnvelope(
                scope=str(envelope.get("scope", "session")),
                limit=float(envelope.get("limit", 0.0)),
                spent=float(envelope.get("spent", 0.0)),
                period=str(envelope.get("period", "session")),
                lambda_cost=float(
                    envelope.get("lambda", envelope.get("lambda_cost", config.lambda_cost))
                ),
                request_ceiling=(
                    float(envelope["request_ceiling"])
                    if envelope.get("request_ceiling") is not None
                    else None
                ),
                estimated_request_cost=(
                    float(envelope["estimated_request_cost"])
                    if envelope.get("estimated_request_cost") is not None
                    else None
                ),
                ramp_multiplier=float(envelope.get("ramp_multiplier", 4.0)),
                exceeded_policy=str(
                    envelope.get("exceeded_policy", "clamp_to_cheapest")
                ),
            )
        except (TypeError, ValueError):
            return None
    return None


def _resolve_lambda(
    config: RouteConfig,
    envelope: BudgetEnvelope | dict[str, Any] | None,
) -> tuple[float, list[str], BudgetEnvelope | None]:
    """Resolve λ from envelope (with ramp) or RouteConfig; record constraints."""
    constraints: list[str] = []
    env = _as_envelope(envelope, config)
    if env is None:
        return config.lambda_cost, constraints, None
    constraints.append(f"envelope:{env.scope}")
    if env.is_exceeded():
        constraints.append("envelope:exceeded")
    return env.effective_lambda(config.lambda_cost), constraints, env


def _fail_open(
    config: RouteConfig,
    *,
    reason: str,
    task_class_id: str = DEFAULT_TASK_CLASS,
    lambda_cost: float | None = None,
    constraints_applied: list[str] | None = None,
) -> RouteDecisionResult:
    lam = config.lambda_cost if lambda_cost is None else lambda_cost
    q = config.default_quality
    c = config.default_cost
    s = bandit_score(q, c, lam)
    logger.warning("route fail-open: %s → %s", reason, config.default_model_version_id)
    return RouteDecisionResult(
        selected_model_version_id=config.default_model_version_id,
        task_class_id=task_class_id,
        score=s,
        lambda_cost=lam,
        scores={config.default_model_version_id: s},
        rationale=f"fail-open: {reason}",
        fail_open=True,
        default_reason=reason,
        decided_at=_now_iso(),
        constraints_applied=list(constraints_applied or []),
    )


def _persist_decision(
    result: RouteDecisionResult,
    store: GraphStore | None,
) -> RouteDecisionResult:
    """Persist RouteDecision when a store is provided; never raise to caller."""
    if store is None:
        return result
    try:
        rid = result.route_decision_id or f"urn:mg:routedecision:{uuid.uuid4().hex[:12]}"
        result.route_decision_id = rid
        store.append_route_decision(
            result.to_attrs(),
            decision_id=rid,
            at=result.decided_at or None,
        )
    except Exception:  # noqa: BLE001 — persistence must not block fail-open path
        logger.exception("route decision persistence failed (continuing)")
    return result


def decide(
    request: str,
    *,
    config: RouteConfig | None = None,
    candidates: list[dict[str, Any]] | None = None,
    posterior: BanditPosterior | None = None,
    graph_snapshot: dict[str, Any] | None = None,
    envelope: BudgetEnvelope | dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    store: GraphStore | None = None,
    trajectory_id: str | None = None,
    episode_id: str | None = None,
    hop_index: int | None = None,
) -> RouteDecisionResult:
    """Select a model version or return the configured default.

    Fail-open on any exception, empty candidates, or corrupt inputs.
    When the budget envelope is exceeded, clamp to cheapest allowed candidate
    (or configured default) — see ``compass.route.envelope`` module docstring.
    When ``policy`` is provided, ``compass.serve.governance`` filters eligibility
    (deny providers, PII-local-only, budget ceilings). Missing/corrupt policy
    engines fail-open. When ``store`` is provided, persist a RouteDecision node
    (including fail-open outcomes). Persistence errors are logged and swallowed.
    """
    cfg = config or RouteConfig()
    constraints: list[str] = []
    lam = cfg.lambda_cost
    env: BudgetEnvelope | None = None

    try:
        # Governance (Pillar 4): filter candidates + optional org budget merge.
        # Missing/corrupt policy engine → fail-open (unconstrained).
        gov = None
        try:
            from compass.serve.governance import apply_policy_engine

            cand_pre = list(candidates or [])
            cand_pre, gov_constraints, envelope, gov = apply_policy_engine(
                cand_pre, policy, envelope=envelope
            )
            candidates = cand_pre
            constraints.extend(gov_constraints)
        except Exception:  # noqa: BLE001 — policy engine must never block Route
            logger.exception("governance policy engine failed — fail-open")
            constraints.append("governance:missing_engine")

        lam, constraints_env, env = _resolve_lambda(cfg, envelope)
        constraints.extend(constraints_env)
        # Keep unique order-preserving constraint tags.
        seen: set[str] = set()
        deduped: list[str] = []
        for c in constraints:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        constraints = deduped

        if graph_snapshot is not None and not isinstance(graph_snapshot, dict):
            result = _fail_open(
                cfg,
                reason="corrupt_graph",
                lambda_cost=lam,
                constraints_applied=constraints,
            )
            result.trajectory_id = trajectory_id
            result.episode_id = episode_id
            result.hop_index = hop_index
            return _persist_decision(result, store)

        task_class = classify(request, graph_snapshot)

        cand_list = list(candidates or [])
        if not cand_list:
            empty_reason = "empty_candidates"
            if gov is not None:
                empty_reason = (
                    "governance_block"
                    if getattr(gov, "enforce_block", False)
                    else "governance_filtered_empty"
                )
                if "governance:no_eligible" not in constraints:
                    constraints.append("governance:no_eligible")
                if getattr(gov, "enforce_block", False):
                    constraints.append("governance:enforce_block")
                else:
                    constraints.append("governance:fail_open")
            result = _fail_open(
                cfg,
                reason=empty_reason,
                task_class_id=task_class,
                lambda_cost=lam,
                constraints_applied=constraints,
            )
            result.trajectory_id = trajectory_id
            result.episode_id = episode_id
            result.hop_index = hop_index
            return _persist_decision(result, store)

        bandit = posterior or BanditPosterior()
        scores: dict[str, float] = {}
        for cand in cand_list:
            mid = str(cand.get("id") or cand.get("model_version_id") or "")
            if not mid:
                continue
            arm = bandit.get_arm(task_class, mid)
            quality = float(cand.get("quality", bandit.expected_quality(arm)))
            cost = float(cand.get("cost", arm.cost_mean if arm.cost_mean else cfg.default_cost))
            scores[mid] = bandit_score(quality, cost, lam)

        if not scores:
            result = _fail_open(
                cfg,
                reason="empty_candidates",
                task_class_id=task_class,
                lambda_cost=lam,
                constraints_applied=constraints,
            )
            result.trajectory_id = trajectory_id
            result.episode_id = episode_id
            result.hop_index = hop_index
            return _persist_decision(result, store)

        # Envelope exceeded → clamp (documented fail-open), else best score.
        if env is not None and env.is_exceeded():
            selected_id, tag = env.resolve_exceeded_selection(
                cand_list,
                default_model_version_id=cfg.default_model_version_id,
                default_cost=cfg.default_cost,
            )
            if tag not in constraints:
                constraints.append(tag)
            # If clamp picked a candidate not in scores (configured default with
            # no matching cand), synthesize a fail-open-ish score entry.
            if selected_id not in scores:
                q = cfg.default_quality
                c = cfg.default_cost
                scores[selected_id] = bandit_score(q, c, lam)
                rationale = (
                    f"envelope exceeded → {tag}; using configured default"
                )
                fail_open = True
                default_reason = "envelope_exceeded"
            else:
                rationale = (
                    f"envelope exceeded → {tag}; clamped from score winner"
                )
                fail_open = False
                default_reason = None
            result = RouteDecisionResult(
                selected_model_version_id=selected_id,
                task_class_id=task_class,
                score=scores[selected_id],
                lambda_cost=lam,
                scores=scores,
                rationale=rationale,
                fail_open=fail_open,
                default_reason=default_reason,
                decided_at=_now_iso(),
                constraints_applied=constraints,
            )
            result.trajectory_id = trajectory_id
            result.episode_id = episode_id
            result.hop_index = hop_index
            return _persist_decision(result, store)

        best_id = max(scores, key=scores.get)  # type: ignore[arg-type]
        result = RouteDecisionResult(
            selected_model_version_id=best_id,
            task_class_id=task_class,
            score=scores[best_id],
            lambda_cost=lam,
            scores=scores,
            rationale="highest score under quality−λ·cost",
            fail_open=False,
            default_reason=None,
            decided_at=_now_iso(),
            constraints_applied=constraints,
        )
        result.trajectory_id = trajectory_id
        result.episode_id = episode_id
        result.hop_index = hop_index
        return _persist_decision(result, store)
    except Exception as exc:  # noqa: BLE001 — fail-open discipline
        logger.exception("route decide exception")
        result = _fail_open(
            cfg,
            reason=f"exception:{type(exc).__name__}",
            lambda_cost=lam,
            constraints_applied=constraints,
        )
        result.trajectory_id = trajectory_id
        result.episode_id = episode_id
        result.hop_index = hop_index
        return _persist_decision(result, store)
