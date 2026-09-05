"""Track N Pillar 3 — managed fleet capability graph stub."""

from __future__ import annotations

import pytest

from compass.fleet import (
    ENV_FLEET_OPT_IN,
    FleetCapabilityGraphStub,
    FleetIngestConfig,
    FleetIngestRefused,
    InMemorySharedGraphStore,
    anonymize_snapshot,
    is_fleet_opt_in,
)
from compass.probe.tos_policy import TosViolation


def test_fleet_default_opt_out(monkeypatch):
    monkeypatch.delenv(ENV_FLEET_OPT_IN, raising=False)
    assert is_fleet_opt_in() is False
    stub = FleetCapabilityGraphStub(config=FleetIngestConfig(fail_open=True))
    result = stub.ingest(
        "tenant-a",
        {"nodes": [{"id": "o1", "kind": "Observation", "attrs": {"provider": "huggingface"}}]},
    )
    assert result.ok is False
    assert result.opted_in is False
    assert "opt-in" in (result.reason or "").lower()


def test_fleet_opt_in_required_raises_when_not_fail_open(monkeypatch):
    monkeypatch.delenv(ENV_FLEET_OPT_IN, raising=False)
    stub = FleetCapabilityGraphStub(config=FleetIngestConfig(opt_in=False, fail_open=False))
    with pytest.raises(FleetIngestRefused):
        stub.ingest("t", {"nodes": []})


def test_anonymize_strips_secrets_and_pii():
    snap = anonymize_snapshot(
        {
            "tenant_id": "acme",
            "api_key": "sk-secret",
            "user_email": "a@b.c",
            "nodes": [
                {
                    "id": "urn:mg:observation:1",
                    "kind": "Observation",
                    "attrs": {
                        "provider": "huggingface",
                        "api_key": "nope",
                        "prompt": "secret prompt",
                        "fleet_redistribute": True,
                        "comparative": True,
                        "quality": {"mean": 0.8, "n": 3, "ci95": 0.1},
                    },
                }
            ],
        },
        tenant_id="acme-corp",
    )
    assert "api_key" not in snap
    assert snap.get("anonymized") is True
    assert snap["public_leaderboard"] is False
    assert snap["tenant_pseudonym"].startswith("t_")
    assert "tenant_id" not in snap
    node = snap["nodes"][0]
    assert "api_key" not in node["attrs"]
    assert "prompt" not in node["attrs"]
    assert node["attrs"]["tenant_pseudonym"] == snap["tenant_pseudonym"]


def test_ingest_opt_in_merges_anonymized(monkeypatch):
    monkeypatch.setenv(ENV_FLEET_OPT_IN, "1")
    store = InMemorySharedGraphStore()
    stub = FleetCapabilityGraphStub(store=store, config=FleetIngestConfig())
    result = stub.ingest(
        "tenant-b",
        {
            "nodes": [
                {
                    "id": "urn:mg:observation:hf1",
                    "kind": "Observation",
                    "attrs": {
                        "provider": "huggingface",
                        "model_version_id": "hf/x",
                        "fleet_redistribute": True,
                        "comparative": True,
                        "quality": {"mean": 0.9, "n": 5, "ci95": 0.05},
                        "cost": {"mean": 0.01, "n": 5, "ci95": 0.0},
                    },
                }
            ]
        },
    )
    assert result.ok is True
    assert result.ingested == 1
    snap = store.snapshot()
    assert snap["fleet"] is True
    assert snap["public_leaderboard"] is False
    assert len(snap["nodes"]) == 1


def test_denylist_drops_forbidden_comparative_nodes():
    stub = FleetCapabilityGraphStub(
        config=FleetIngestConfig(opt_in=True, fail_open=True)
    )
    # openai comparative fleet redistribute is denied — anonymize drops node
    result = stub.ingest(
        "tenant-c",
        {
            "nodes": [
                {
                    "id": "urn:mg:observation:oa1",
                    "kind": "Observation",
                    "attrs": {
                        "provider": "openai",
                        "fleet_redistribute": True,
                        "comparative": True,
                        "quality": {"mean": 0.9, "n": 2, "ci95": 0.2},
                    },
                },
                {
                    "id": "urn:mg:observation:hf2",
                    "kind": "Observation",
                    "attrs": {
                        "provider": "huggingface",
                        "fleet_redistribute": True,
                        "comparative": True,
                        "quality": {"mean": 0.7, "n": 2, "ci95": 0.2},
                    },
                },
            ]
        },
    )
    assert result.ok is True
    assert result.tos_blocked >= 1
    assert result.ingested == 1  # only huggingface survives anonymize gate
