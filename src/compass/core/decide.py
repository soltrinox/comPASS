"""Pure decide() over a host-fed snapshot — WASM / browser entrypoint.

No GraphStore, no filesystem, no env key lookup, no probe/ingest/serve imports.
Fail-open reason codes come from ``compass.core.defaults`` (parity table).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from compass.core.classify import DEFAULT_TASK_CLASS, classify
from compass.core.defaults import (
    DEFAULT_COST,
    DEFAULT_LAMBDA,
    DEFAULT_MODEL_VERSION_ID,
    DEFAULT_QUALITY,
    FAIL_OPEN_DEFAULTS,
    MODULE_TRAP,
    NO_CANDIDATES,
    SNAPSHOT_CORRUPT,
    SNAPSHOT_MISSING,
)
from compass.core.score_read import score_candidates
from compass.core.snapshot import GraphSnapshot, parse_snapshot
from compass.score.bandit import BanditPosterior, score as bandit_score

logger = logging.getLogger(__name__)


@dataclass
class CoreRouteConfig:
    """Hot-path config for the WASM core. Never holds provider credentials."""

    default_model_version_id: str = DEFAULT_MODEL_VERSION_ID
    lambda_cost: float = DEFAULT_LAMBDA
    default_quality: float = DEFAULT_QUALITY
    default_cost: float = DEFAULT_COST


@dataclass
class CoreDecision:
    """RouteDecision-shaped result for host / proxy consumption (JSON-friendly)."""

    selected_model_version_id: str
    task_class_id: str
    score: float
    lambda_cost: float
    scores: dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    fail_open: bool = False
    default_reason: str | None = None
    decided_at: str = ""
    constraints_applied: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "selected_model_version_id": self.selected_model_version_id,
            "task_class_id": self.task_class_id,
            "score": self.score,
            "lambda": self.lambda_cost,
            "scores": dict(self.scores),
            "rationale": self.rationale,
            "fail_open": self.fail_open,
            "default_reason": self.default_reason,
            "decided_at": self.decided_at,
            "constraints_applied": list(self.constraints_applied),
        }


def _fail(
    cfg: CoreRouteConfig,
    *,
    reason_code: str,
    task_class_id: str = DEFAULT_TASK_CLASS,
    lambda_cost: float | None = None,
    decided_at: str = "",
    constraints_applied: list[str] | None = None,
) -> CoreDecision:
    fo = FAIL_OPEN_DEFAULTS.get(reason_code)
    rationale = fo.rationale if fo else f"fail-open: {reason_code}"
    lam = cfg.lambda_cost if lambda_cost is None else lambda_cost
    s = bandit_score(cfg.default_quality, cfg.default_cost, lam)
    logger.warning("core decide fail-open: %s → %s", reason_code, cfg.default_model_version_id)
    return CoreDecision(
        selected_model_version_id=cfg.default_model_version_id,
        task_class_id=task_class_id,
        score=s,
        lambda_cost=lam,
        scores={cfg.default_model_version_id: s},
        rationale=rationale,
        fail_open=True,
        default_reason=reason_code,
        decided_at=decided_at,
        constraints_applied=list(constraints_applied or []),
    )


def decide_from_snapshot(
    request: str,
    snapshot: GraphSnapshot | bytes | str | dict[str, Any] | None,
    *,
    config: CoreRouteConfig | None = None,
    candidates: list[dict[str, Any]] | None = None,
    posterior: BanditPosterior | None = None,
    lambda_cost: float | None = None,
    now_iso: str = "",
) -> CoreDecision:
    """Classify + score + decide against an immutable snapshot.

    ``now_iso`` is supplied by the host clock import (no wall-clock in pure tests
    unless the caller passes it). Missing/corrupt snapshot → fail-open.
    """
    cfg = config or CoreRouteConfig()
    lam = cfg.lambda_cost if lambda_cost is None else float(lambda_cost)
    constraints: list[str] = []

    try:
        snap = snapshot if isinstance(snapshot, GraphSnapshot) else parse_snapshot(snapshot)
        if not snap.ok:
            code = snap.error_code or SNAPSHOT_CORRUPT.code
            if code == SNAPSHOT_MISSING.code:
                return _fail(cfg, reason_code=SNAPSHOT_MISSING.code, lambda_cost=lam, decided_at=now_iso)
            return _fail(cfg, reason_code=SNAPSHOT_CORRUPT.code, lambda_cost=lam, decided_at=now_iso)

        task_class = classify(request, {"schema": snap.schema, "nodes": list(snap.nodes)})
        cand_list = list(candidates) if candidates is not None else snap.candidates_from_nodes()
        if not cand_list:
            return _fail(
                cfg,
                reason_code=NO_CANDIDATES.code,
                task_class_id=task_class,
                lambda_cost=lam,
                decided_at=now_iso,
                constraints_applied=constraints,
            )

        scores = score_candidates(
            cand_list,
            task_class_id=task_class,
            lambda_cost=lam,
            posterior=posterior,
            default_quality=cfg.default_quality,
            default_cost=cfg.default_cost,
        )
        if not scores:
            return _fail(
                cfg,
                reason_code=NO_CANDIDATES.code,
                task_class_id=task_class,
                lambda_cost=lam,
                decided_at=now_iso,
                constraints_applied=constraints,
            )

        # Overlapping / clear winner: pick max score; ties → lower cost among tied ids
        best_score = max(scores.values())
        tied = [mid for mid, sc in scores.items() if sc == best_score]
        if len(tied) > 1:
            cost_by_id = {
                str(c.get("id") or c.get("model_version_id")): float(c.get("cost", cfg.default_cost))
                for c in cand_list
                if (c.get("id") or c.get("model_version_id"))
            }
            tied.sort(key=lambda mid: (cost_by_id.get(mid, cfg.default_cost), mid))
            constraints.append("tie_break:lower_cost")
        best_id = tied[0]
        return CoreDecision(
            selected_model_version_id=best_id,
            task_class_id=task_class,
            score=scores[best_id],
            lambda_cost=lam,
            scores=scores,
            rationale="highest score under quality−λ·cost",
            fail_open=False,
            default_reason=None,
            decided_at=now_iso,
            constraints_applied=constraints,
        )
    except Exception as exc:  # noqa: BLE001 — fail-open discipline (module_trap)
        logger.exception("core decide trap")
        return _fail(
            cfg,
            reason_code=MODULE_TRAP.code,
            lambda_cost=lam,
            decided_at=now_iso,
            constraints_applied=[f"exception:{type(exc).__name__}"],
        )
