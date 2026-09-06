"""Track O: generic LLM adapter — decide / catalog / proxy override."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass.route.decide import RouteConfig
from compass.serve.adapter import (
    MODE_CATALOG,
    MODE_DECIDE,
    MODE_PROXY,
    AdapterConfig,
    adapt_chat_completions,
    build_target_url,
    host_allowed,
    strip_compass,
)
from compass.serve.proxy import ProxyConfig, handle_chat_completions, route_completion_body

CANDIDATES = [
    {
        "id": "cheap",
        "quality": 0.7,
        "cost": 0.1,
        "served_id": "cheap-served",
        "upstream": "http://catalog-cheap.example",
    },
    {
        "id": "pricey",
        "quality": 0.95,
        "cost": 1.0,
        "upstream": "http://catalog-pricey.example",
    },
]


def test_strip_compass_removes_extension():
    body = {"model": "x", "messages": [], "compass": {"selection_mode": "decide"}}
    out = strip_compass(body)
    assert "compass" not in out
    assert out["model"] == "x"
    assert "compass" in body  # original untouched


def test_build_target_url_object_and_shorthand():
    assert (
        build_target_url(
            {
                "target": {
                    "scheme": "http",
                    "host": "192.168.1.50",
                    "port": 8080,
                    "path": "/v1/chat/completions",
                }
            }
        )
        == "http://192.168.1.50:8080/v1/chat/completions"
    )
    assert (
        build_target_url({"target_url": "http://10.0.0.5:9/v1/chat/completions"})
        == "http://10.0.0.5:9/v1/chat/completions"
    )
    # target_url wins
    assert (
        build_target_url(
            {
                "target_url": "http://a/v1/chat/completions",
                "target": {"host": "b"},
            }
        )
        == "http://a/v1/chat/completions"
    )


def test_host_allowlist_deny_by_default():
    url = "http://evil.example/v1/chat/completions"
    assert host_allowed(url, None) is True
    assert host_allowed(url, []) is False
    assert host_allowed(url, ["evil.example"]) is True
    assert host_allowed(url, ["example"]) is True  # subdomain suffix
    assert host_allowed(url, ["other.com"]) is False


def test_decide_mode_default():
    cfg = AdapterConfig(candidates=CANDIDATES, route_config=RouteConfig(lambda_cost=1.0))
    result = adapt_chat_completions(
        {"model": "ignored", "messages": [{"role": "user", "content": "implement a function"}]},
        config=cfg,
    )
    assert result.selection_mode == MODE_DECIDE
    assert result.model == "cheap"
    assert result.decision.selection_mode == MODE_DECIDE
    assert "compass" not in result.outbound_body
    assert result.upstream_url == "http://catalog-cheap.example/v1/chat/completions"


def test_catalog_pin_by_model_version_id():
    cfg = AdapterConfig(candidates=CANDIDATES)
    result = adapt_chat_completions(
        {
            "model": "ignored",
            "messages": [{"role": "user", "content": "hi"}],
            "compass": {"model_version_id": "pricey"},
        },
        config=cfg,
    )
    assert result.selection_mode == MODE_CATALOG
    assert result.model == "pricey"
    assert result.upstream_url == "http://catalog-pricey.example/v1/chat/completions"


def test_catalog_pin_by_top_level_model():
    cfg = AdapterConfig(candidates=CANDIDATES)
    result = adapt_chat_completions(
        {
            "model": "cheap-served",
            "messages": [{"role": "user", "content": "hi"}],
        },
        config=cfg,
    )
    assert result.selection_mode == MODE_CATALOG
    assert result.model == "cheap"


def test_proxy_override_priority_over_catalog():
    cfg = AdapterConfig(candidates=CANDIDATES, host_allowlist=None)
    result = adapt_chat_completions(
        {
            "model": "pricey",
            "messages": [{"role": "user", "content": "hi"}],
            "compass": {
                "model_version_id": "pricey",
                "target": {
                    "scheme": "http",
                    "host": "127.0.0.1",
                    "port": 9000,
                    "model": "local-llama",
                },
            },
        },
        config=cfg,
    )
    assert result.selection_mode == MODE_PROXY
    assert result.model == "local-llama"
    assert result.upstream_url == "http://127.0.0.1:9000/v1/chat/completions"
    assert "compass" not in result.outbound_body


def test_proxy_override_denied_allowlist():
    cfg = AdapterConfig(candidates=CANDIDATES, host_allowlist=["allowed.example"])
    result = adapt_chat_completions(
        {
            "messages": [{"role": "user", "content": "hi"}],
            "compass": {"target_url": "http://evil.example/v1/chat/completions"},
        },
        config=cfg,
    )
    assert result.denied is True
    assert result.deny_reason == "proxy_host_denied"
    assert result.upstream_url is None


def test_handle_denied_returns_403():
    cfg = ProxyConfig(candidates=CANDIDATES, host_allowlist=["ok.test"])
    status, payload, _ = handle_chat_completions(
        {
            "messages": [{"role": "user", "content": "hi"}],
            "compass": {"target": {"host": "nope.test", "scheme": "http"}},
        },
        config=cfg,
    )
    assert status == 403
    assert payload["compass"]["denied"] is True


def test_catalog_miss_fail_open():
    cfg = AdapterConfig(
        candidates=CANDIDATES,
        route_config=RouteConfig(default_model_version_id="fallback"),
    )
    result = adapt_chat_completions(
        {
            "messages": [{"role": "user", "content": "hi"}],
            "compass": {"model_version_id": "does-not-exist"},
        },
        config=cfg,
    )
    assert result.selection_mode == MODE_CATALOG
    assert result.model == "fallback"
    assert result.decision.fail_open is True


def test_catalog_miss_fallback_to_decide():
    cfg = AdapterConfig(candidates=CANDIDATES, route_config=RouteConfig(lambda_cost=1.0))
    result = adapt_chat_completions(
        {
            "model": "ignored",
            "messages": [{"role": "user", "content": "implement a function"}],
            "compass": {
                "model_version_id": "missing",
                "fallback_to_decide": True,
            },
        },
        config=cfg,
    )
    assert result.selection_mode == MODE_DECIDE
    assert result.model == "cheap"


def test_compress_on_hop():
    calls = []

    def hook(body, result):
        calls.append(result.model)
        b = dict(body)
        b["_compressed"] = True
        return b

    cfg = AdapterConfig(
        candidates=CANDIDATES,
        previous_model="other",
        compress_hook=hook,
    )
    result = adapt_chat_completions(
        {
            "model": "ignored",
            "messages": [{"role": "user", "content": "implement a function"}],
            "compass": {"compress": {"enabled": True}},
        },
        config=cfg,
    )
    assert result.compressed is True
    assert result.outbound_body.get("_compressed") is True
    assert calls == [result.model]


def test_route_completion_body_strips_compass():
    cfg = ProxyConfig(candidates=CANDIDATES)
    model, decision, outbound = route_completion_body(
        {
            "model": "ignored",
            "messages": [{"role": "user", "content": "implement a function"}],
            "compass": {"selection_mode": "decide", "secret": "nope"},
        },
        config=cfg,
    )
    assert "compass" not in outbound
    assert model in {"cheap", "pricey"}
    assert decision.selection_mode == MODE_DECIDE


def test_evidence_folder(tmp_path, monkeypatch):
    """Write Track O evidence summary under test-results/o-generic-adapter/."""
    root = Path(__file__).resolve().parents[1]
    out = root / "test-results" / "o-generic-adapter"
    out.mkdir(parents=True, exist_ok=True)
    cfg = AdapterConfig(candidates=CANDIDATES)
    modes = {}
    for name, body in [
        ("decide", {"model": "ignored", "messages": [{"role": "user", "content": "implement a function"}]}),
        (
            "catalog",
            {
                "messages": [{"role": "user", "content": "x"}],
                "compass": {"model_version_id": "pricey"},
            },
        ),
        (
            "proxy",
            {
                "messages": [{"role": "user", "content": "x"}],
                "compass": {
                    "target_url": "http://127.0.0.1:1/v1/chat/completions",
                    "target": {"host": "127.0.0.1"},
                },
            },
        ),
    ]:
        r = adapt_chat_completions(body, config=cfg)
        modes[name] = {
            "selection_mode": r.selection_mode,
            "model": r.model,
            "has_compass_outbound": "compass" in r.outbound_body,
            "upstream": r.upstream_url,
        }
    summary = {"track": "O", "modes": modes, "ok": True}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert (out / "summary.json").is_file()
