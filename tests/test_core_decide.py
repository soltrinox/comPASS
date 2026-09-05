"""Core decide_from_snapshot fail-open parity (Python stand-in for WASM)."""

from __future__ import annotations

import json
from pathlib import Path

from compass.core.decide import CoreRouteConfig, decide_from_snapshot
from compass.core.snapshot import parse_snapshot

# decide_from_snapshot is re-imported inside trap test after patch for safety

FIXTURE = Path(__file__).resolve().parents[1] / "wasmer" / "fixtures" / "snapshot_min.json"


def test_parse_missing_and_corrupt():
    assert parse_snapshot(None).error_code == "snapshot_missing"
    assert parse_snapshot(b"").error_code == "snapshot_missing"
    assert parse_snapshot(b"{not-json").error_code == "snapshot_corrupt"
    assert parse_snapshot(["nope"]).error_code == "snapshot_corrupt"  # type: ignore[arg-type]


def test_decide_missing_snapshot_fail_open():
    r = decide_from_snapshot("hello", None)
    assert r.fail_open is True
    assert r.default_reason == "snapshot_missing"
    assert r.selected_model_version_id == "default"


def test_decide_corrupt_snapshot_fail_open():
    r = decide_from_snapshot("hello", b"{truncated")
    assert r.fail_open is True
    assert r.default_reason == "snapshot_corrupt"


def test_decide_no_candidates_fail_open():
    snap = {"schema": "model-graph/v1", "nodes": [], "edges": []}
    r = decide_from_snapshot("hello", snap)
    assert r.fail_open is True
    assert r.default_reason == "no_candidates"


def test_decide_fixture_selects_cheaper():
    raw = FIXTURE.read_bytes()
    r = decide_from_snapshot(
        "implement a function",
        raw,
        config=CoreRouteConfig(lambda_cost=1.0),
        now_iso="2026-09-05T00:00:00Z",
    )
    assert r.fail_open is False
    assert r.selected_model_version_id == "urn:mg:model:cheap"
    assert r.task_class_id == "code_generation"
    assert r.decided_at == "2026-09-05T00:00:00Z"
    payload = r.to_json_dict()
    assert "lambda" in payload
    assert payload["fail_open"] is False


def test_decide_module_trap_fail_open(monkeypatch):
    import compass.core.decide as decide_mod

    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(decide_mod, "classify", boom)
    raw = FIXTURE.read_bytes()
    r = decide_mod.decide_from_snapshot(
        "x", raw, config=CoreRouteConfig(default_model_version_id="fb")
    )
    assert r.fail_open is True
    assert r.default_reason == "module_trap"
    assert r.selected_model_version_id == "fb"
