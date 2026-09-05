"""Tier 2 Advisor: advisory write + freshness rules (CC-9 contract)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from compass.route.decide import RouteDecisionResult, decide
from compass.serve.advisory import (
    ADVISORY_SCHEMA,
    build_advisory_payload,
    format_advisory_markdown,
    is_fresh,
    required_fields_present,
    write_advisory,
)


def _decision() -> RouteDecisionResult:
    return decide(
        "refactor these modules across packages",
        candidates=[
            {"id": "urn:mg:modelversion:cheap", "quality": 0.82, "cost": 0.11},
            {"id": "urn:mg:modelversion:pricey", "quality": 0.85, "cost": 0.94},
        ],
    )


def test_build_payload_from_route_decision():
    result = _decision()
    result.route_decision_id = "urn:mg:routedecision:test"
    payload = build_advisory_payload(
        result,
        model_id="cursor-grok-4.6-high-fast",
        provider="cursor",
        ttl_seconds=300,
        scores_summary=[
            {"model_id": "X", "quality_mean": 0.82, "n": 40, "est_cost_per_task": 0.11},
            {"model_id": "Y", "quality_mean": 0.85, "n": 40, "est_cost_per_task": 0.94},
        ],
        rationale=(
            "Across your last 40 tasks of this class, X scored 0.82 at $0.11/task; "
            "Y scored 0.85 at $0.94/task."
        ),
    )
    assert payload["schema"] == ADVISORY_SCHEMA
    assert payload["task_class"]
    assert payload["recommendation"]["model_id"] == "cursor-grok-4.6-high-fast"
    assert payload["recommendation"]["provider"] == "cursor"
    assert payload["route_decision_id"] == "urn:mg:routedecision:test"
    assert payload["written_at"].endswith("Z")
    assert payload["expires_at"].endswith("Z")
    assert is_fresh(payload)


def test_write_advisory_json_and_markdown(tmp_path: Path):
    dest = tmp_path / "advisory" / "latest.json"
    result = _decision()
    result.route_decision_id = "urn:mg:routedecision:write"
    doc = write_advisory(
        dest,
        result,
        model_id="model-x",
        provider="cursor",
        ttl_seconds=120,
        strict=True,
    )
    assert doc is not None
    assert dest.is_file()
    loaded = json.loads(dest.read_text(encoding="utf-8"))
    assert loaded["schema"] == ADVISORY_SCHEMA
    assert loaded["recommendation"]["model_id"] == "model-x"
    md = dest.with_suffix(".md")
    assert md.is_file()
    text = md.read_text(encoding="utf-8")
    assert "comPASS advisory" in text
    assert "model-x" in text
    assert "Advisory only" in text


def test_freshness_future_ok_past_stale():
    now = datetime(2026, 9, 5, 12, 0, 0, tzinfo=timezone.utc)
    base = build_advisory_payload(
        {
            "task_class_id": "multi_file_refactor",
            "selected_model_version_id": "urn:mg:modelversion:abc",
            "scores": {"urn:mg:modelversion:abc": 0.71},
            "lambda": 1.0,
            "rationale": "test",
            "route_decision_id": "urn:mg:routedecision:fresh",
        },
        model_id="abc",
        provider="cursor",
        ttl_seconds=300,
        written_at=now,
    )
    assert is_fresh(base, now=now + timedelta(seconds=1))
    assert is_fresh(base, now=now + timedelta(seconds=299))
    assert not is_fresh(base, now=now + timedelta(seconds=301))
    assert not is_fresh(base, now=now + timedelta(hours=1))


def test_freshness_rejects_malformed_and_missing_fields():
    assert not is_fresh(None)
    assert not is_fresh("not-json")
    assert not is_fresh({"schema": ADVISORY_SCHEMA})
    assert not required_fields_present(
        {
            "schema": ADVISORY_SCHEMA,
            "written_at": "2026-09-05T00:00:00Z",
            "expires_at": "2026-09-05T00:05:00Z",
            "task_class": "x",
            "recommendation": {},  # missing model_id
        }
    )
    bad_expiry = build_advisory_payload(
        {"task_class_id": "general", "selected_model_version_id": "m", "scores": {}},
        model_id="m",
        written_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    bad_expiry["expires_at"] = "not-a-timestamp"
    assert not is_fresh(bad_expiry)


def test_write_advisory_soft_fail_on_oserror(tmp_path: Path, monkeypatch):
    """Writer soft-fails (returns None) so callers can fail-open."""
    dest = tmp_path / "advisory" / "latest.json"

    def boom(self, *_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", boom)
    out = write_advisory(
        dest,
        {"task_class_id": "general", "selected_model_version_id": "m", "scores": {}},
        model_id="m",
        strict=False,
    )
    assert out is None


def test_format_markdown_includes_score_summary():
    payload = build_advisory_payload(
        {"task_class_id": "code_generation", "selected_model_version_id": "m1", "scores": {}},
        model_id="m1",
        provider="cursor",
        scores_summary=[
            {"model_id": "X", "quality_mean": 0.82, "n": 40, "est_cost_per_task": 0.11}
        ],
        rationale="X is cheaper at similar quality.",
    )
    md = format_advisory_markdown(payload)
    assert "quality=0.82" in md
    assert "est_cost=0.11" in md
    assert "X is cheaper" in md
