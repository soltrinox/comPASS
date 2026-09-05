"""Track N Pillar 4 — enterprise governance policy hooks."""

from __future__ import annotations

from compass.graph import GraphStore, GraphStoreConfig
from compass.route.decide import RouteConfig, decide
from compass.route.envelope import BudgetEnvelope
from compass.serve.governance import (
    GovernancePolicy,
    audit_record_from_decision,
    filter_candidates,
)
from compass.serve.proxy import ProxyConfig, handle_chat_completions
from compass.serve.sdk import route_chat_request


CANDIDATES = [
    {"id": "openai/gpt", "provider": "openai", "quality": 0.95, "cost": 0.5},
    {"id": "local-llama", "provider": "local", "local": True, "quality": 0.8, "cost": 0.05},
    {"id": "hf/small", "provider": "huggingface", "quality": 0.7, "cost": 0.1},
]


def test_deny_provider_selects_alternative():
    result = decide(
        "implement a function",
        config=RouteConfig(default_model_version_id="fallback"),
        candidates=CANDIDATES,
        policy={"deny_providers": ["openai"]},
    )
    assert result.fail_open is False
    assert result.selected_model_version_id != "openai/gpt"
    assert "governance" in result.constraints_applied


def test_pii_local_only_forces_local():
    result = decide(
        "summarize this SSN document",
        config=RouteConfig(default_model_version_id="fallback"),
        candidates=CANDIDATES,
        policy={"pii_local_only": True},
    )
    assert result.selected_model_version_id == "local-llama"
    assert any("pii_local_only" in c for c in result.constraints_applied)


def test_all_denied_fail_open_default():
    result = decide(
        "hello",
        config=RouteConfig(default_model_version_id="fallback"),
        candidates=CANDIDATES,
        policy={
            "deny_providers": ["openai", "huggingface", "local"],
            "enforce_block": False,
        },
    )
    assert result.fail_open is True
    assert result.selected_model_version_id == "fallback"
    assert result.default_reason == "governance_filtered_empty"
    assert "governance:fail_open" in result.constraints_applied


def test_enforce_block_soft_still_returns_decision():
    result = decide(
        "hello",
        config=RouteConfig(default_model_version_id="fallback"),
        candidates=CANDIDATES,
        policy={
            "deny_model_ids": ["openai/gpt", "local-llama", "hf/small"],
            "enforce_block": True,
        },
    )
    assert result.fail_open is True
    assert result.default_reason == "governance_block"
    assert "governance:enforce_block" in result.constraints_applied


def test_budget_ceiling_via_policy_envelope():
    result = decide(
        "implement a function",
        config=RouteConfig(lambda_cost=1.0, default_model_version_id="fallback"),
        candidates=[
            {"id": "pricey", "provider": "openai", "quality": 0.99, "cost": 1.0},
            {"id": "cheap", "provider": "huggingface", "quality": 0.7, "cost": 0.01},
        ],
        policy={"budget_ceiling": 1.0, "budget_spent": 1.0},
    )
    # Exceeded → clamp_to_cheapest
    assert result.selected_model_version_id == "cheap"
    assert any("envelope:exceeded" in c or "governance:budget" in c for c in result.constraints_applied)


def test_missing_policy_engine_fail_open_unchanged():
    # Corrupt policy type → ignore (fail-open)
    result = decide(
        "implement a function",
        candidates=[
            {"id": "a", "quality": 0.9, "cost": 0.1},
            {"id": "b", "quality": 0.5, "cost": 0.1},
        ],
        policy="not-a-mapping",  # type: ignore[arg-type]
    )
    assert result.fail_open is False
    assert result.selected_model_version_id == "a"
    assert "governance:missing_engine" in result.constraints_applied


def test_audit_trail_from_persisted_route_decision(tmp_path):
    cfg = GraphStoreConfig(root=tmp_path / "g")
    with GraphStore(cfg) as store:
        result = decide(
            "fix a bug",
            candidates=CANDIDATES,
            policy={"deny_providers": ["openai"]},
            store=store,
        )
        assert result.route_decision_id
        audit = audit_record_from_decision(
            result, context_digest="sha256:abc", cost=0.05, outcome="ok"
        )
        assert audit["schema"] == "governance-audit/v1"
        assert audit["route_decision_id"] == result.route_decision_id
        assert audit["model"] == result.selected_model_version_id
        assert "governance" in audit["constraints_applied"]
        nodes = store.find_route_decisions(route_decision_id=result.route_decision_id)
        assert len(nodes) == 1


def test_proxy_enforces_governance_policy():
    cfg = ProxyConfig(
        candidates=CANDIDATES,
        policy={"pii_local_only": True},
        route_config=RouteConfig(default_model_version_id="fallback"),
    )
    status, body, _ctype = handle_chat_completions(
        {"model": "ignored", "messages": [{"role": "user", "content": "PII task"}]},
        config=cfg,
    )
    assert status == 200
    assert isinstance(body, dict)
    assert body["model"] == "local-llama"
    assert body["compass"]["route_decision"]["selected_model_version_id"] == "local-llama"


def test_filter_candidates_unit():
    gov = GovernancePolicy(deny_providers={"openai"}, pii_local_only=False)
    eligible, tags = filter_candidates(CANDIDATES, gov)
    ids = {c["id"] for c in eligible}
    assert "openai/gpt" not in ids
    assert "local-llama" in ids
    assert "governance" in tags
