"""Tier 3: SDK wrapper, OpenAI-compatible proxy dry-run, budget envelope clamp."""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from compass.graph import GraphStore, GraphStoreConfig
from compass.route.decide import RouteConfig, decide
from compass.route.envelope import (
    EXCEEDED_CLAMP_TO_CHEAPEST,
    EXCEEDED_CONFIGURED_DEFAULT,
    BudgetEnvelope,
)
from compass.serve.proxy import (
    ProxyConfig,
    create_asgi_app,
    dry_run_response,
    handle_chat_completions,
    make_handler,
    route_completion_body,
)
from compass.serve.sdk import extract_prompt_text, route_chat_request


CANDIDATES = [
    {"id": "cheap", "quality": 0.7, "cost": 0.1},
    {"id": "pricey", "quality": 0.95, "cost": 1.0},
]


def test_extract_prompt_from_messages():
    text = extract_prompt_text(
        {
            "model": "ignored",
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "please fix this bug"},
            ],
        }
    )
    assert "fix this bug" in text


def test_sdk_route_chat_request_selects_model():
    routed = route_chat_request(
        {"messages": [{"role": "user", "content": "implement a function"}]},
        config=RouteConfig(lambda_cost=1.0, default_model_version_id="default"),
        candidates=CANDIDATES,
    )
    assert routed.model == "cheap"
    assert routed.decision.fail_open is False
    assert routed.decision.task_class_id == "code_generation"
    d = routed.to_dict()
    assert d["model"] == "cheap"
    assert "route_decision" in d


def test_sdk_fail_open_on_empty_candidates():
    routed = route_chat_request(
        {"messages": [{"role": "user", "content": "hi"}]},
        config=RouteConfig(default_model_version_id="fallback-x"),
        candidates=[],
    )
    assert routed.model == "fallback-x"
    assert routed.decision.fail_open is True


def test_sdk_persists_when_store(tmp_path):
    with GraphStore(GraphStoreConfig(root=tmp_path / "g")) as store:
        routed = route_chat_request(
            {"messages": [{"role": "user", "content": "implement a function"}]},
            candidates=[{"id": "m1", "quality": 0.8, "cost": 0.1}],
            store=store,
        )
        assert routed.decision.route_decision_id
        doc = store.load_document(fail_open=False)
        assert any(n["kind"] == "RouteDecision" for n in doc.nodes)


def test_envelope_lambda_ramps_with_utilization():
    low = BudgetEnvelope(scope="session", limit=10.0, spent=0.0, lambda_cost=1.0)
    high = BudgetEnvelope(scope="session", limit=10.0, spent=10.0, lambda_cost=1.0)
    assert low.effective_lambda() == pytest.approx(1.0)
    assert high.effective_lambda() == pytest.approx(4.0)  # ramp_multiplier default
    assert high.is_exceeded() is True


def test_envelope_exceeded_clamps_to_cheapest():
    env = BudgetEnvelope(
        scope="session",
        limit=1.0,
        spent=1.5,
        lambda_cost=1.0,
        exceeded_policy=EXCEEDED_CLAMP_TO_CHEAPEST,
    )
    # Without clamp, pricey might win on quality; with clamp → cheap
    result = decide(
        "implement a function",
        config=RouteConfig(lambda_cost=0.01, default_model_version_id="default"),
        envelope=env,
        candidates=CANDIDATES,
    )
    assert result.selected_model_version_id == "cheap"
    assert any("clamp_to_cheapest" in c for c in result.constraints_applied)
    assert "envelope:exceeded" in result.constraints_applied


def test_envelope_exceeded_configured_default():
    env = BudgetEnvelope(
        scope="project",
        limit=1.0,
        spent=2.0,
        exceeded_policy=EXCEEDED_CONFIGURED_DEFAULT,
    )
    result = decide(
        "implement a function",
        config=RouteConfig(default_model_version_id="org-default"),
        envelope=env,
        candidates=CANDIDATES,
    )
    assert result.selected_model_version_id == "org-default"
    assert result.fail_open is True
    assert result.default_reason == "envelope_exceeded"


def test_envelope_request_ceiling_exceeded():
    env = BudgetEnvelope(
        scope="request",
        limit=100.0,
        spent=0.0,
        request_ceiling=0.2,
        estimated_request_cost=0.5,
    )
    assert env.request_exceeded() is True
    result = decide(
        "summarize",
        envelope=env,
        candidates=CANDIDATES,
        config=RouteConfig(default_model_version_id="default"),
    )
    assert result.selected_model_version_id == "cheap"


def test_proxy_dry_run_handler():
    body = {
        "model": "client-picked",
        "messages": [{"role": "user", "content": "please fix this bug in the function"}],
    }
    cfg = ProxyConfig(
        upstream=None,
        route_config=RouteConfig(default_model_version_id="default"),
        candidates=CANDIDATES,
    )
    status, payload, ctype = handle_chat_completions(body, config=cfg)
    assert status == 200
    assert ctype == "application/json"
    assert isinstance(payload, dict)
    assert payload["compass"]["dry_run"] is True
    assert payload["model"] == "cheap"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert "route_decision" in payload["compass"]


def test_proxy_stdlib_http_server_dry_run():
    cfg = ProxyConfig(upstream=None, candidates=CANDIDATES)
    handler = make_handler(cfg)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://{host}:{port}/v1/chat/completions",
            data=json.dumps(
                {
                    "model": "x",
                    "messages": [{"role": "user", "content": "implement a function"}],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        assert data["compass"]["dry_run"] is True
        assert data["model"] == "cheap"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_proxy_asgi_dry_run_with_httpx():
    """Optional: needs httpx (pip install -e '.[sdk]'). Uses asyncio.run — no pytest-asyncio."""
    import asyncio

    httpx = pytest.importorskip("httpx")
    cfg = ProxyConfig(upstream=None, candidates=CANDIDATES)
    app = create_asgi_app(cfg)

    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/v1/chat/completions",
                json={
                    "model": "ignored",
                    "messages": [{"role": "user", "content": "implement a function"}],
                },
            )

    r = asyncio.run(_run())
    assert r.status_code == 200
    data = r.json()
    assert data["compass"]["dry_run"] is True
    assert data["model"] == "cheap"


def test_route_completion_body_rewrites_model():
    cfg = ProxyConfig(candidates=CANDIDATES)
    model, decision, outbound = route_completion_body(
        {"model": "client", "messages": [{"role": "user", "content": "fix bug"}]},
        config=cfg,
    )
    assert outbound["model"] == model == "cheap"
    assert decision.selected_model_version_id == "cheap"


def test_dry_run_response_shape():
    decision = decide("hi", candidates=[{"id": "m", "quality": 0.5, "cost": 0.1}])
    payload = dry_run_response("m", decision, original_model="orig")
    assert payload["object"] == "chat.completion"
    assert payload["compass"]["dry_run"] is True
