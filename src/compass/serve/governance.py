"""Paid Pillar 4 — enterprise governance policy hooks (test-ready spike).

Enforcement surfaces (not reporting-only):
- deny providers / model ids
- PII → local-only endpoint eligibility
- budget ceilings (via envelope + optional policy ceiling)

**Fail-open (documented):** when the policy engine is missing/corrupt, Route
continues with unconstrained candidates (free path). When policy *is* present
and denies an endpoint, Route selects an eligible alternative. If none remain:
- default ``enforce_block=False`` → fail-open to configured Route default
  (constraint tag ``governance:fail_open``); never raises to the user.
- ``enforce_block=True`` → still returns a RouteDecision (no hard HTTP block
  unless the proxy chooses to map ``default_reason=governance_block``), with
  ``fail_open=True`` and rationale noting enforce-block. Documented choice:
  we do **not** raise exceptions on the prompt path.

Audit trail consumes persisted ``RouteDecision`` fields via
``audit_record_from_decision``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping

from compass.route.decide import RouteDecisionResult
from compass.route.envelope import BudgetEnvelope

logger = logging.getLogger(__name__)

# Documented fail-open modes when no eligible candidates remain after policy.
GOVERNANCE_FAIL_OPEN = "fail_open_default"
GOVERNANCE_ENFORCE_BLOCK = "enforce_block_soft"  # soft = still returns decision


@dataclass
class GovernancePolicy:
    """Org routing constraints enforced at decide / proxy.

    Accepts dict construction via ``from_mapping`` for the existing
    ``decide(..., policy={...})`` call shape.
    """

    deny_providers: set[str] = field(default_factory=set)
    deny_model_ids: set[str] = field(default_factory=set)
    allow_providers: set[str] | None = None  # if set, only these providers
    pii_local_only: bool = False
    # Optional org budget ceiling — merged into envelope when present.
    budget_ceiling: float | None = None
    budget_spent: float = 0.0
    # When True and no eligible candidates: tag as governance_block (still
    # returns fail-open decision — never raises on prompt path).
    enforce_block: bool = False
    # Data residency hint (filter tag only in this spike).
    data_residency: str | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any] | None) -> "GovernancePolicy | None":
        if raw is None:
            return None
        if isinstance(raw, GovernancePolicy):
            return raw
        if not isinstance(raw, Mapping):
            return None
        try:
            deny_p = raw.get("deny_providers") or raw.get("denied_providers") or []
            deny_m = raw.get("deny_model_ids") or raw.get("denied_models") or []
            allow_p = raw.get("allow_providers")
            return cls(
                deny_providers={str(x).lower() for x in deny_p},
                deny_model_ids={str(x) for x in deny_m},
                allow_providers=(
                    {str(x).lower() for x in allow_p} if allow_p is not None else None
                ),
                pii_local_only=bool(
                    raw.get("pii_local_only")
                    or raw.get("pii") == "local_only"
                    or raw.get("data_classification") == "pii"
                ),
                budget_ceiling=(
                    float(raw["budget_ceiling"])
                    if raw.get("budget_ceiling") is not None
                    else (
                        float(raw["limit"])
                        if raw.get("limit") is not None and raw.get("scope") == "org"
                        else None
                    )
                ),
                budget_spent=float(raw.get("budget_spent") or raw.get("spent") or 0.0),
                enforce_block=bool(raw.get("enforce_block", False)),
                data_residency=(
                    str(raw["data_residency"])
                    if raw.get("data_residency") is not None
                    else None
                ),
            )
        except (TypeError, ValueError):
            logger.warning("corrupt governance policy — fail-open (ignore policy)")
            return None


def _candidate_provider(cand: Mapping[str, Any]) -> str:
    return str(
        cand.get("provider")
        or cand.get("source_provider")
        or cand.get("endpoint_provider")
        or ""
    ).lower()


def _candidate_id(cand: Mapping[str, Any]) -> str:
    return str(cand.get("id") or cand.get("model_version_id") or "")


def _is_local(cand: Mapping[str, Any]) -> bool:
    if cand.get("local") is True or cand.get("is_local") is True:
        return True
    provider = _candidate_provider(cand)
    if provider in {"local", "ollama", "llama.cpp", "lmstudio", "vllm-local"}:
        return True
    mid = _candidate_id(cand).lower()
    return mid.startswith("local") or "local" in mid or mid.endswith("-local")


def filter_candidates(
    candidates: list[dict[str, Any]],
    policy: GovernancePolicy | Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Apply eligibility filters; return (eligible, constraint_tags).

    Missing/corrupt policy → unchanged candidates + empty constraints (fail-open).
    """
    gov = (
        policy
        if isinstance(policy, GovernancePolicy)
        else GovernancePolicy.from_mapping(policy if isinstance(policy, Mapping) else None)
    )
    if gov is None:
        return list(candidates), []

    constraints: list[str] = ["governance"]
    out: list[dict[str, Any]] = []
    for cand in candidates:
        mid = _candidate_id(cand)
        provider = _candidate_provider(cand)
        if mid and mid in gov.deny_model_ids:
            constraints.append(f"governance:deny_model:{mid}")
            continue
        if provider and provider in gov.deny_providers:
            constraints.append(f"governance:deny_provider:{provider}")
            continue
        if gov.allow_providers is not None:
            # Local always allowed when pii_local_only; else must be in allow set.
            if provider not in gov.allow_providers and not (
                gov.pii_local_only and _is_local(cand)
            ):
                constraints.append(f"governance:allowlist_miss:{provider or mid}")
                continue
        if gov.pii_local_only and not _is_local(cand):
            constraints.append(f"governance:pii_local_only:deny:{mid or provider}")
            continue
        if gov.data_residency:
            residency = str(cand.get("data_residency") or cand.get("region") or "")
            if residency and residency != gov.data_residency:
                constraints.append(
                    f"governance:residency:{residency}!={gov.data_residency}"
                )
                continue
        out.append(cand)

    if gov.pii_local_only:
        constraints.append("governance:pii_local_only")
    if gov.deny_providers:
        constraints.append("governance:deny_providers")
    if gov.budget_ceiling is not None:
        constraints.append("governance:budget_ceiling")
    return out, constraints


def merge_budget_envelope(
    envelope: BudgetEnvelope | dict[str, Any] | None,
    policy: GovernancePolicy | Mapping[str, Any] | None,
) -> BudgetEnvelope | dict[str, Any] | None:
    """If policy carries an org budget ceiling, ensure an envelope exists."""
    gov = (
        policy
        if isinstance(policy, GovernancePolicy)
        else GovernancePolicy.from_mapping(policy if isinstance(policy, Mapping) else None)
    )
    if gov is None or gov.budget_ceiling is None:
        return envelope
    if isinstance(envelope, BudgetEnvelope):
        # Tighten limit if policy ceiling is lower.
        if envelope.limit <= 0 or gov.budget_ceiling < envelope.limit:
            envelope.limit = float(gov.budget_ceiling)
        envelope.spent = max(float(envelope.spent), float(gov.budget_spent))
        return envelope
    if isinstance(envelope, dict):
        limit = float(envelope.get("limit") or 0.0)
        if limit <= 0 or gov.budget_ceiling < limit:
            envelope = dict(envelope)
            envelope["limit"] = float(gov.budget_ceiling)
            envelope["spent"] = max(
                float(envelope.get("spent") or 0.0), float(gov.budget_spent)
            )
            envelope.setdefault("scope", "org")
        return envelope
    return BudgetEnvelope(
        scope="org",
        limit=float(gov.budget_ceiling),
        spent=float(gov.budget_spent),
        period="org",
    )


def audit_record_from_decision(
    decision: RouteDecisionResult | Mapping[str, Any],
    *,
    context_digest: str | None = None,
    cost: float | None = None,
    outcome: str | None = None,
) -> dict[str, Any]:
    """Build an audit trail record from persisted RouteDecision fields."""
    if isinstance(decision, RouteDecisionResult):
        attrs = decision.to_attrs()
        rid = decision.route_decision_id
        score = decision.score
    else:
        attrs = dict(decision)
        rid = attrs.get("route_decision_id") or attrs.get("id")
        score = attrs.get("score")
    return {
        "schema": "governance-audit/v1",
        "route_decision_id": rid,
        "model": attrs.get("selected_model_version_id"),
        "task_class_id": attrs.get("task_class_id"),
        "context_digest": context_digest,
        "cost": cost if cost is not None else attrs.get("lambda"),
        "score": score,
        "outcome": outcome,
        "constraints_applied": list(attrs.get("constraints_applied") or []),
        "fail_open": bool(attrs.get("fail_open")),
        "default_reason": attrs.get("default_reason"),
        "rationale": attrs.get("rationale"),
        "decided_at": attrs.get("decided_at"),
        "trajectory_id": attrs.get("trajectory_id"),
        "episode_id": attrs.get("episode_id"),
    }


def apply_policy_engine(
    candidates: list[dict[str, Any]],
    policy: GovernancePolicy | Mapping[str, Any] | None,
    *,
    envelope: BudgetEnvelope | dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str], BudgetEnvelope | dict[str, Any] | None, GovernancePolicy | None]:
    """Single entry used by decide(): filter + merge budget; fail-open on None."""
    gov = (
        policy
        if isinstance(policy, GovernancePolicy)
        else GovernancePolicy.from_mapping(policy if isinstance(policy, Mapping) else None)
    )
    if gov is None and policy is not None and not isinstance(policy, (GovernancePolicy, Mapping)):
        # Corrupt type — fail-open.
        return list(candidates), ["governance:missing_engine"], envelope, None
    if gov is None:
        return list(candidates), [], envelope, None
    filtered, constraints = filter_candidates(candidates, gov)
    env = merge_budget_envelope(envelope, gov)
    return filtered, constraints, env, gov


__all__ = [
    "GOVERNANCE_ENFORCE_BLOCK",
    "GOVERNANCE_FAIL_OPEN",
    "GovernancePolicy",
    "apply_policy_engine",
    "audit_record_from_decision",
    "filter_candidates",
    "merge_budget_envelope",
]
