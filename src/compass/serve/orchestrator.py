"""Tier 4 session orchestrator: per-turn hop planning with hop_legal + band gate.

Consults ``decide()`` for model choice, a ``hop_legal``-style gate (callable
injected or local predicate), and an equivalence-band gate. Declines hops when
the confidence band is too wide. Never claims identical text across models —
only outcome equivalence within a stated band (prototype §16).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from compass.route.decide import RouteConfig, RouteDecisionResult, decide

logger = logging.getLogger(__name__)

HopLegalFn = Callable[[], bool]


@dataclass
class EquivalenceBand:
    """Published per-task-class outcome-equivalence band (not identical text)."""

    task_class_id: str
    width: float
    n: int = 0
    ci95: float | None = None
    substitutable: bool = True
    note: str = "outcome equivalence within band; never identical text"

    @property
    def effective_width(self) -> float:
        if self.ci95 is not None:
            return float(self.ci95)
        return float(self.width)


@dataclass
class OrchestratorConfig:
    """Session orchestrator knobs."""

    route: RouteConfig = field(default_factory=RouteConfig)
    max_band_width: float = 0.25
    default_quota_shares: dict[str, float] = field(
        default_factory=lambda: {"open": 0.40, "decision": 0.35, "path": 0.25}
    )


@dataclass
class PayloadShapeNotes:
    """Advisory notes for compressor hot_set quota shaping (stub, not enforcement)."""

    recipient_id: str
    quota_shares: dict[str, float]
    rationale: str
    identical_text_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipient_id": self.recipient_id,
            "quota_shares": dict(self.quota_shares),
            "rationale": self.rationale,
            "identical_text_claimed": False,
            "equivalence_scope": "task_outcome_within_band",
        }


@dataclass
class HopPlan:
    """Per-turn hop plan produced by the session orchestrator."""

    hop: bool
    current_recipient_id: str | None
    selected_recipient_id: str
    decision: RouteDecisionResult
    declined_reason: str | None = None
    hop_legal: bool = True
    band_ok: bool = True
    payload_notes: PayloadShapeNotes | None = None
    equivalence_note: str = (
        "Outcome equivalence within a confidence band; never identical text."
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hop": self.hop,
            "current_recipient_id": self.current_recipient_id,
            "selected_recipient_id": self.selected_recipient_id,
            "declined_reason": self.declined_reason,
            "hop_legal": self.hop_legal,
            "band_ok": self.band_ok,
            "equivalence_note": self.equivalence_note,
            "payload_notes": None
            if self.payload_notes is None
            else self.payload_notes.to_dict(),
            "route_decision": self.decision.to_attrs(),
            "route_decision_id": self.decision.route_decision_id,
        }


def local_hop_legal(*, pending_tool: bool = False) -> bool:
    """Local hop_legal-style predicate: illegal if pending tool state flag set."""
    return not bool(pending_tool)


def band_allows_hop(
    band: EquivalenceBand | Mapping[str, Any] | None,
    *,
    max_width: float,
) -> tuple[bool, str | None]:
    """Return (ok, reason). Wide bands are not substitutable — decline hop."""
    if band is None:
        return True, None
    if isinstance(band, EquivalenceBand):
        eb = band
    else:
        width_raw = band.get("width", band.get("ci95", 1.0))
        eb = EquivalenceBand(
            task_class_id=str(band.get("task_class_id") or band.get("task_class") or ""),
            width=float(width_raw if width_raw is not None else 1.0),
            n=int(band.get("n", 0) or 0),
            ci95=(float(band["ci95"]) if band.get("ci95") is not None else None),
            substitutable=bool(band.get("substitutable", True)),
        )
    width = eb.effective_width
    if not eb.substitutable or width > float(max_width):
        return False, f"equivalence_band_too_wide:width={width:.4f}>max={max_width:.4f}"
    return True, None


def shape_payload_notes(
    recipient_id: str,
    *,
    capabilities: Mapping[str, Any] | None = None,
    config: OrchestratorConfig | None = None,
) -> PayloadShapeNotes:
    """Capability-aware payload shaping stub — varies hot_set quota shares."""
    cfg = config or OrchestratorConfig()
    shares = dict(cfg.default_quota_shares)
    caps = dict(capabilities or {})
    long_ctx = caps.get("long_context_fidelity")
    if isinstance(long_ctx, (int, float)) and float(long_ctx) < 0.5:
        shares = {"open": 0.45, "decision": 0.40, "path": 0.15}
        rationale = (
            f"recipient {recipient_id}: low long_context_fidelity -> "
            "tighter path/heading quota, richer open-item/decision digest"
        )
    else:
        rationale = (
            f"recipient {recipient_id}: default hot_set quota shares "
            f"(open={shares['open']}, decision={shares['decision']}, path={shares['path']})"
        )
    return PayloadShapeNotes(
        recipient_id=recipient_id,
        quota_shares=shares,
        rationale=rationale,
        identical_text_claimed=False,
    )


class SessionOrchestrator:
    """Plans per-turn model hops inside one continuous session (Tier 4)."""

    def __init__(
        self,
        *,
        config: OrchestratorConfig | None = None,
        hop_legal: HopLegalFn | None = None,
        bands: Mapping[str, EquivalenceBand | Mapping[str, Any]] | None = None,
    ) -> None:
        self.config = config or OrchestratorConfig()
        self._hop_legal = hop_legal
        self.bands: dict[str, EquivalenceBand | Mapping[str, Any]] = dict(bands or {})

    def set_hop_legal(self, fn: HopLegalFn | None) -> None:
        self._hop_legal = fn

    def check_hop_legal(self, *, pending_tool: bool | None = None) -> bool:
        if self._hop_legal is not None:
            try:
                return bool(self._hop_legal())
            except Exception:  # noqa: BLE001
                logger.exception("hop_legal callable failed; treating as illegal")
                return False
        if pending_tool is None:
            return True
        return local_hop_legal(pending_tool=pending_tool)

    def plan_turn(
        self,
        request: str,
        *,
        current_recipient_id: str | None,
        candidates: list[dict[str, Any]] | None = None,
        pending_tool: bool = False,
        capabilities: Mapping[str, Mapping[str, Any]] | None = None,
        envelope: Any = None,
        store: Any = None,
        force_recipient_id: str | None = None,
    ) -> HopPlan:
        """Plan whether to hop this turn and which recipient to use."""
        legal = self.check_hop_legal(pending_tool=pending_tool)
        decision = decide(
            request,
            config=self.config.route,
            candidates=candidates,
            envelope=envelope,
            store=store,
        )
        selected = force_recipient_id or decision.selected_model_version_id
        caps_map = capabilities or {}
        notes = shape_payload_notes(
            selected,
            capabilities=caps_map.get(selected),
            config=self.config,
        )

        if not legal:
            stay = current_recipient_id or selected
            return HopPlan(
                hop=False,
                current_recipient_id=current_recipient_id,
                selected_recipient_id=stay,
                decision=decision,
                declined_reason="hop_illegal_pending_tool",
                hop_legal=False,
                band_ok=True,
                payload_notes=notes
                if stay == selected
                else shape_payload_notes(
                    stay,
                    capabilities=caps_map.get(stay),
                    config=self.config,
                ),
            )

        band = self.bands.get(decision.task_class_id)
        band_ok, band_reason = band_allows_hop(
            band, max_width=self.config.max_band_width
        )
        would_hop = (
            current_recipient_id is not None and selected != current_recipient_id
        )

        if would_hop and not band_ok:
            assert current_recipient_id is not None
            return HopPlan(
                hop=False,
                current_recipient_id=current_recipient_id,
                selected_recipient_id=current_recipient_id,
                decision=decision,
                declined_reason=band_reason,
                hop_legal=True,
                band_ok=False,
                payload_notes=shape_payload_notes(
                    current_recipient_id,
                    capabilities=caps_map.get(current_recipient_id),
                    config=self.config,
                ),
            )

        return HopPlan(
            hop=bool(would_hop),
            current_recipient_id=current_recipient_id,
            selected_recipient_id=selected,
            decision=decision,
            declined_reason=None,
            hop_legal=True,
            band_ok=True if band is None else band_ok,
            payload_notes=notes,
        )
