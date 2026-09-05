"""Route decide() fail-open, scoring, envelope λ, RouteDecision persistence."""

from __future__ import annotations

import compass.route.decide as decide_mod
from compass.graph import GraphStore, GraphStoreConfig
from compass.route.classify import classify
from compass.route.decide import RouteConfig, decide
from compass.route.envelope import BudgetEnvelope


def test_classify_keyword_code():
    assert classify("please fix this bug in the function") == "code_generation"


def test_classify_empty_is_general():
    assert classify("") == "general"


def test_decide_empty_candidates_fail_open():
    result = decide("hello", candidates=[])
    assert result.fail_open is True
    assert result.default_reason == "empty_candidates"
    assert result.selected_model_version_id == "default"
    assert "fail-open" in result.rationale


def test_decide_corrupt_graph_fail_open():
    result = decide("hello", graph_snapshot=["not", "a", "dict"])  # type: ignore[arg-type]
    assert result.fail_open is True
    assert result.default_reason == "corrupt_graph"


def test_decide_exception_fail_open(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(decide_mod, "classify", boom)
    cfg = RouteConfig(default_model_version_id="fallback-model")
    result = decide("x", config=cfg, candidates=[{"id": "m1"}])
    assert result.fail_open is True
    assert result.selected_model_version_id == "fallback-model"
    assert result.default_reason and result.default_reason.startswith("exception:")


def test_decide_scores_quality_minus_lambda_cost():
    cfg = RouteConfig(lambda_cost=1.0, default_model_version_id="default")
    result = decide(
        "implement a function",
        config=cfg,
        candidates=[
            {"id": "cheap", "quality": 0.7, "cost": 0.1},
            {"id": "pricey", "quality": 0.75, "cost": 0.5},
        ],
    )
    assert result.fail_open is False
    assert result.selected_model_version_id == "cheap"
    assert result.scores["cheap"] == 0.6
    assert result.task_class_id == "code_generation"


def test_decide_to_attrs_shape():
    result = decide("json schema please", candidates=[{"id": "m", "quality": 0.9, "cost": 0.1}])
    attrs = result.to_attrs()
    assert attrs["fail_open"] is False
    assert "selected_model_version_id" in attrs
    assert "lambda" in attrs
    assert "constraints_applied" in attrs


def test_envelope_lambda_scalar_affects_score():
    env = BudgetEnvelope(scope="session", limit=10.0, spent=0.0, lambda_cost=10.0)
    result = decide(
        "implement a function",
        config=RouteConfig(lambda_cost=1.0),
        envelope=env,
        candidates=[
            {"id": "cheap", "quality": 0.7, "cost": 0.1},
            {"id": "pricey", "quality": 0.9, "cost": 0.05},
        ],
    )
    # With λ=10: cheap 0.7-1.0=-0.3; pricey 0.9-0.5=0.4 → pricey
    assert result.fail_open is False
    assert result.lambda_cost == 10.0
    assert result.selected_model_version_id == "pricey"
    assert "envelope:session" in result.constraints_applied


def test_decide_persists_route_decision(tmp_path):
    cfg_store = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg_store) as store:
        result = decide(
            "implement a function",
            candidates=[{"id": "m1", "quality": 0.8, "cost": 0.1}],
            store=store,
        )
        assert result.fail_open is False
        assert result.route_decision_id
        doc = store.load_document(fail_open=False)
        rds = [n for n in doc.nodes if n["kind"] == "RouteDecision"]
        assert len(rds) == 1
        assert rds[0]["id"] == result.route_decision_id
        assert rds[0]["attrs"]["selected_model_version_id"] == "m1"
        assert any(e["kind"] == "selected" for e in doc.edges)


def test_decide_fail_open_still_persists(tmp_path):
    cfg_store = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg_store) as store:
        result = decide("hello", candidates=[], store=store)
        assert result.fail_open is True
        assert result.route_decision_id
        doc = store.load_document(fail_open=False)
        rds = [n for n in doc.nodes if n["kind"] == "RouteDecision"]
        assert len(rds) == 1
        assert rds[0]["attrs"]["fail_open"] is True
        assert rds[0]["attrs"]["default_reason"] == "empty_candidates"
