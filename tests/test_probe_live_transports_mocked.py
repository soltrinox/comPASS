"""Mocked HTTP suite: HF/OpenRouter/Cursor catalog+canary, denylist, rate limit, Route isolation."""

from __future__ import annotations

import ast
import json
import sys
import importlib
from pathlib import Path

import pytest

from compass.graph import GraphStore, GraphStoreConfig
from compass.ingest import cursor, huggingface, openrouter
from compass.probe.http_transport import HttpResponse, MockHttpTransport
from compass.probe.live_transports import (
    CURSOR_MODELS_URL,
    HF_MODELS_URL,
    OPENROUTER_CHAT_URL,
    OPENROUTER_MODELS_URL,
    fetch_live_catalog,
    run_live_canary,
)
from compass.probe.network_gate import NETWORK_ENV, ProbeNetworkDenied
from compass.probe.observations import persist_observation, capability_figure
from compass.probe.rate_limit import ProviderRateLimiter, RateLimitConfig, RateLimitExceeded
from compass.probe.runner import run_probe
from compass.probe.tos_policy import TosViolation, gate_observation_payload
from compass.schema import SCHEMA_ID, GraphDocument
import compass.route.decide as route_decide

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
PROOF = REPO / "test-results" / "f-live-probe"


def _json_bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


@pytest.fixture(autouse=True)
def _network_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "1")


@pytest.fixture(autouse=True)
def _fast_limiter(monkeypatch: pytest.MonkeyPatch):
    """Avoid real sleeps from the process-wide DEFAULT_LIMITER across tests."""
    import compass.probe.live_transports as lt
    import compass.probe.rate_limit as rl

    fast = ProviderRateLimiter(
        default=RateLimitConfig(
            max_concurrent=8,
            min_interval_s=0.0,
            max_calls_per_minute=10_000,
            budget_cap=10_000,
            backoff_base_s=0.0,
            backoff_max_s=0.0,
            jitter_s=0.0,
        ),
        sleep_fn=lambda _s: None,
    )
    monkeypatch.setattr(rl, "DEFAULT_LIMITER", fast)
    monkeypatch.setattr(lt, "DEFAULT_LIMITER", fast)


def test_hf_openrouter_cursor_catalog_success():
    transport = MockHttpTransport(
        routes={
            ("GET", HF_MODELS_URL): HttpResponse(
                200, _json_bytes([{"id": "org/model-a", "pipeline_tag": "text-generation"}])
            ),
            ("GET", OPENROUTER_MODELS_URL): HttpResponse(
                200,
                _json_bytes(
                    {
                        "data": [
                            {
                                "id": "vendor/model-b",
                                "name": "Model B",
                                "context_length": 8192,
                                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                            }
                        ]
                    }
                ),
            ),
            ("GET", CURSOR_MODELS_URL): HttpResponse(
                200, _json_bytes({"models": [{"id": "cursor-test-1", "name": "Cursor Test"}]})
            ),
        }
    )
    hf = fetch_live_catalog("huggingface", transport=transport, token="tok")
    or_ = fetch_live_catalog("openrouter", transport=transport, token="tok")
    cu = fetch_live_catalog("cursor", transport=transport, token="tok")
    assert hf.network_used and hf.entries[0]["served_id"] == "org/model-a"
    assert or_.entries[0]["served_id"] == "vendor/model-b"
    assert cu.entries[0]["served_id"] == "cursor-test-1"
    assert len(transport.calls) == 3


def test_catalog_4xx_and_timeout():
    transport = MockHttpTransport(
        routes={
            ("GET", OPENROUTER_MODELS_URL): HttpResponse(401, b"unauthorized"),
            ("GET", HF_MODELS_URL): TimeoutError("simulated timeout"),
        }
    )
    with pytest.raises(RuntimeError, match="HTTP 401"):
        fetch_live_catalog("openrouter", transport=transport, token="x")
    with pytest.raises(TimeoutError):
        fetch_live_catalog("huggingface", transport=transport, token="x")


def test_canary_success_and_4xx():
    ok = MockHttpTransport(
        routes={
            ("POST", OPENROUTER_CHAT_URL): HttpResponse(
                200, _json_bytes({"choices": [{"message": {"content": "hello"}}]})
            )
        }
    )
    r = run_live_canary("openrouter", "vendor/m", "ping", transport=ok, token="t")
    assert r.network_used and r.fingerprint.startswith("fp_") and r.error is None

    bad = MockHttpTransport(
        routes={("POST", OPENROUTER_CHAT_URL): HttpResponse(429, b"rate")}
    )
    r2 = run_live_canary("openrouter", "vendor/m", "ping", transport=bad, token="t")
    assert r2.error == "HTTP 429"


def test_live_denied_when_network_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "0")
    with pytest.raises(ProbeNetworkDenied):
        fetch_live_catalog("openrouter", transport=MockHttpTransport(), token="t")


def test_ingest_live_fail_open_to_fixtures(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "0")
    # live=True but gate off → fixtures
    hf = huggingface.fetch_catalog(live=True)
    or_ = openrouter.fetch_catalog(live=True)
    cu = cursor.fetch_catalog(live=True)
    assert len(hf) >= 2 and len(or_) >= 2 and len(cu) >= 1


def test_ingest_live_uses_transport(monkeypatch: pytest.MonkeyPatch):
    transport = MockHttpTransport(
        routes={
            ("GET", OPENROUTER_MODELS_URL): HttpResponse(
                200,
                _json_bytes({"data": [{"id": "live/or", "name": "Live", "pricing": {}}]}),
            )
        }
    )
    entries = openrouter.fetch_catalog(live=True, transport=transport, token="t")
    assert entries[0]["served_id"] == "live/or"
    assert entries[0]["card_source"] == "openrouter:live"


def test_tos_denylist_blocks_fleet_redistribute():
    with pytest.raises(TosViolation):
        gate_observation_payload(
            {
                "provider": "openai",
                "fleet_redistribute": True,
                "comparative": True,
                "quality": {"mean": 0.9, "n": 10, "ci95": 0.1},
            }
        )
    # local / non-fleet ok for openrouter
    gated = gate_observation_payload(
        {
            "provider": "openrouter",
            "fleet_redistribute": False,
            "comparative": False,
            "quality": {"mean": 0.5, "n": 1, "ci95": 0.5},
        }
    )
    assert gated["fleet_redistribute"] is False
    assert gated["public_leaderboard"] is False


def test_cursor_fleet_redistribute_denied():
    with pytest.raises(TosViolation):
        gate_observation_payload(
            {"provider": "cursor", "fleet_redistribute": True, "comparative": True}
        )


def test_rate_limiter_budget_cap():
    sleeps: list[float] = []
    clock = {"t": 1000.0}

    def advance_sleep(dt: float) -> None:
        sleeps.append(dt)
        clock["t"] += max(dt, 0.0)

    lim = ProviderRateLimiter(
        default=RateLimitConfig(
            max_concurrent=2,
            min_interval_s=0.0,
            max_calls_per_minute=100,
            budget_cap=3,
            jitter_s=0.0,
        ),
        sleep_fn=advance_sleep,
        clock=lambda: clock["t"],
    )
    lim.acquire("openrouter")
    lim.release("openrouter")
    lim.acquire("openrouter")
    lim.release("openrouter")
    lim.acquire("openrouter")
    lim.release("openrouter")
    with pytest.raises(RateLimitExceeded):
        lim.acquire("openrouter")
    snap = lim.snapshot()
    assert snap["openrouter"]["calls_total"] == 3
    PROOF.mkdir(parents=True, exist_ok=True)
    (PROOF / "rate-limit-proof.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")


def test_observation_persist_and_supersede_on_fingerprint(tmp_path: Path):
    doc = GraphDocument(schema=SCHEMA_ID, nodes=[], edges=[])
    n1 = persist_observation(
        doc,
        probe_id="urn:mg:probe:t1",
        model_version_id="urn:mg:modelversion:x",
        quality=capability_figure(0.5, 1),
        cost=capability_figure(0.1, 1, 0.05),
        provider="openrouter",
        response_fingerprint="fp_aaa",
        at="2026-09-05T12:00:00Z",
    )
    assert n1["attrs"]["quality"]["mean"] == 0.5
    n2 = persist_observation(
        doc,
        probe_id="urn:mg:probe:t1",
        model_version_id="urn:mg:modelversion:x",
        quality=capability_figure(0.7, 2),
        cost=capability_figure(0.1, 2, 0.04),
        provider="openrouter",
        response_fingerprint="fp_bbb",
        at="2026-09-05T13:00:00Z",
    )
    assert n1["id"] != n2["id"]
    assert doc.node_by_id(n1["id"])["status"] == "superseded"
    assert n2["status"] == "active"
    assert any(e["kind"] == "supersedes" for e in doc.edges)
    assert any(e["kind"] == "observed_on" for e in doc.edges)

    store = GraphStore(GraphStoreConfig(root=tmp_path / "g"))
    store.open()
    store.save_document(doc)
    loaded = store.load_document()
    assert len(loaded.active_nodes(kind="Observation")) == 1


def test_runner_live_with_mock_transport(monkeypatch: pytest.MonkeyPatch):
    transport = MockHttpTransport(
        routes={
            ("POST", OPENROUTER_CHAT_URL): HttpResponse(
                200, _json_bytes({"choices": [{"message": {"content": "ok"}}]})
            )
        }
    )
    result = run_probe(
        "urn:mg:probe:live1",
        mode="live",
        task={
            "provider": "openrouter",
            "model_id": "vendor/m",
            "prompt": "hi",
            "task_class": "code_generation",
        },
        transport=transport,
        token="t",
    )
    assert result.mock is False
    assert result.network_used is True
    assert result.observation["attrs"]["mode"] == "live"


def test_route_decide_never_imports_probe_network_or_http():
    forbidden = {
        "compass.probe.network_gate",
        "compass.probe.live_transports",
        "compass.probe.http_transport",
        "compass.probe.credentials",
        "compass.probe.runner",
    }
    for name in list(sys.modules):
        if name.startswith("compass.probe") or name.startswith("compass.route"):
            del sys.modules[name]
    importlib.import_module("compass.route.decide")
    importlib.import_module("compass.core.decide")
    for mod in forbidden:
        assert mod not in sys.modules, mod

    # Static import audit on route + core sources
    offenders: list[str] = []
    for root in (SRC / "compass" / "route", SRC / "compass" / "core"):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for n in names:
                    if n in forbidden or n.startswith("compass.probe."):
                        offenders.append(f"{path.name}:{n}")
    assert offenders == []


def test_route_decide_fail_open_with_network_denied(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "0")
    # Route path must succeed without touching Probe
    result = route_decide.decide(
        "write a function",
        candidates=[{"id": "urn:mg:modelversion:default"}],
    )
    assert result.selected_model_version_id
    assert result.fail_open in (True, False)


def test_wasmer_crate_has_no_network_gate_refs():
    crate = REPO / "wasmer" / "crate" / "src"
    for path in crate.rglob("*.rs"):
        text = path.read_text(encoding="utf-8")
        assert "network_gate" not in text
        assert "COMPASS_PROBE_ALLOW_NETWORK" not in text
        assert "OPENROUTER_API_KEY" not in text
