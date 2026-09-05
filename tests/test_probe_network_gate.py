"""Network gate: COMPASS_PROBE_ALLOW_NETWORK + host allowlist."""

from __future__ import annotations

import pytest

from compass.probe.network_gate import (
    ALLOWLIST_ENV,
    NETWORK_ENV,
    ProbeNetworkDenied,
    assert_network_allowed,
    configured_allowlist,
    fixture_fallback_reason,
    host_allowed,
    network_allowed,
    parse_host,
)


def test_network_defaults_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(NETWORK_ENV, raising=False)
    assert network_allowed() is False
    with pytest.raises(ProbeNetworkDenied, match="defaults OFF"):
        assert_network_allowed("https://openrouter.ai/api/v1/models")


@pytest.mark.parametrize("val", ["1", "true", "YES", "on"])
def test_network_truthy(monkeypatch: pytest.MonkeyPatch, val: str):
    monkeypatch.setenv(NETWORK_ENV, val)
    assert network_allowed() is True


def test_allowlist_exact_and_subdomain(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "1")
    monkeypatch.delenv(ALLOWLIST_ENV, raising=False)
    assert host_allowed("https://openrouter.ai/api/v1/models")
    assert host_allowed("https://api.openrouter.ai/api/v1/models")
    assert host_allowed("huggingface.co")
    assert not host_allowed("https://evil.example/x")


def test_allowlist_rejects_wildcard(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(ALLOWLIST_ENV, "openrouter.ai,*")
    with pytest.raises(ProbeNetworkDenied, match="wildcard"):
        configured_allowlist()


def test_assert_requires_both_env_and_host(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "1")
    monkeypatch.setenv(ALLOWLIST_ENV, "openrouter.ai")
    assert assert_network_allowed("https://openrouter.ai/foo") == "openrouter.ai"
    with pytest.raises(ProbeNetworkDenied, match="allowlist"):
        assert_network_allowed("https://huggingface.co/api")


def test_parse_host_and_fallback_reason(monkeypatch: pytest.MonkeyPatch):
    assert parse_host("https://api.openrouter.ai:443/x") == "api.openrouter.ai"
    monkeypatch.delenv(NETWORK_ENV, raising=False)
    assert "OFF" in fixture_fallback_reason().upper() or "off" in fixture_fallback_reason()
