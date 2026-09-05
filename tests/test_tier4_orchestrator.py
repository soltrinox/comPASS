"""Tier 4: session orchestrator hop_legal + equivalence-band gate."""

from __future__ import annotations

from compass.route.decide import RouteConfig
from compass.serve.orchestrator import (
    EquivalenceBand,
    OrchestratorConfig,
    SessionOrchestrator,
    band_allows_hop,
    local_hop_legal,
    shape_payload_notes,
)


CANDIDATES = [
    {"id": "model-a", "quality": 0.7, "cost": 0.2},
    {"id": "model-b", "quality": 0.95, "cost": 0.05},
]


def test_local_hop_legal_predicate():
    assert local_hop_legal(pending_tool=False) is True
    assert local_hop_legal(pending_tool=True) is False


def test_decline_hop_when_pending_tool():
    orch = SessionOrchestrator(
        config=OrchestratorConfig(route=RouteConfig(lambda_cost=1.0)),
    )
    plan = orch.plan_turn(
        "implement a function",
        current_recipient_id="model-a",
        candidates=CANDIDATES,
        pending_tool=True,
    )
    assert plan.hop is False
    assert plan.hop_legal is False
    assert plan.declined_reason == "hop_illegal_pending_tool"
    assert plan.selected_recipient_id == "model-a"
    assert "never identical text" in plan.equivalence_note.lower()


def test_injected_hop_legal_callable():
    orch = SessionOrchestrator(hop_legal=lambda: False)
    plan = orch.plan_turn(
        "implement a function",
        current_recipient_id="model-a",
        candidates=CANDIDATES,
    )
    assert plan.hop is False
    assert plan.declined_reason == "hop_illegal_pending_tool"


def test_equivalence_band_too_wide_declines_hop():
    orch = SessionOrchestrator(
        config=OrchestratorConfig(
            max_band_width=0.20, route=RouteConfig(lambda_cost=1.0)
        ),
        bands={
            "code_generation": EquivalenceBand(
                task_class_id="code_generation",
                width=0.50,
                n=12,
                substitutable=False,
            )
        },
    )
    plan = orch.plan_turn(
        "implement a function",
        current_recipient_id="model-a",
        candidates=CANDIDATES,
    )
    assert plan.hop is False
    assert plan.band_ok is False
    assert plan.declined_reason and "equivalence_band_too_wide" in plan.declined_reason
    assert plan.selected_recipient_id == "model-a"


def test_narrow_band_allows_hop():
    orch = SessionOrchestrator(
        config=OrchestratorConfig(
            max_band_width=0.30, route=RouteConfig(lambda_cost=1.0)
        ),
        bands={
            "code_generation": EquivalenceBand(
                task_class_id="code_generation", width=0.10, n=40, ci95=0.08
            )
        },
    )
    plan = orch.plan_turn(
        "implement a function",
        current_recipient_id="model-a",
        candidates=CANDIDATES,
    )
    assert plan.hop is True
    assert plan.selected_recipient_id == "model-b"
    assert plan.payload_notes is not None
    assert plan.payload_notes.identical_text_claimed is False
    d = plan.to_dict()
    assert d["payload_notes"]["identical_text_claimed"] is False


def test_capability_aware_payload_shaping_stub():
    notes = shape_payload_notes(
        "weak-ctx",
        capabilities={"long_context_fidelity": 0.2},
    )
    assert notes.quota_shares["path"] < notes.quota_shares["open"]
    assert notes.identical_text_claimed is False


def test_band_allows_hop_helper():
    ok, reason = band_allows_hop(
        {"width": 0.9, "substitutable": True}, max_width=0.25
    )
    assert ok is False
    assert reason and "too_wide" in reason
