"""Probe runner — execute bandit-chosen probes (dry-run + gated live).

Holds provider credentials in the Probe process only.
Never import this module from route/ or compressor hooks.

Network policy
--------------
* Default mode is **dry-run**: mock Observation payloads, no HTTP.
* Live/network mode requires ``COMPASS_PROBE_ALLOW_NETWORK`` in
  {1, true, yes, on} **and** an allowlisted host.
* Live calls use injectable ``HttpTransport`` (mocked in CI) and
  ``compass.probe.credentials`` for secrets.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from compass.probe.http_transport import HttpTransport
from compass.probe.live_transports import run_live_canary
from compass.probe.network_gate import (
    NETWORK_ENV,
    ProbeNetworkDenied,
    network_allowed,
)
from compass.probe.observations import build_observation_node, capability_figure
from compass.probe.rate_limit import ProviderRateLimiter
from compass.probe.tos_policy import gate_observation_payload

# Re-export for existing tests / callers
ProbeNetworkDisabledError = ProbeNetworkDenied

Mode = Literal["dry-run", "live"]


@dataclass
class ProbeResult:
    """Probe outcome (Observation-shaped attrs)."""

    probe_id: str
    mode: str
    observation: dict[str, Any]
    mock: bool = True
    network_used: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "mode": self.mode,
            "observation": dict(self.observation),
            "mock": self.mock,
            "network_used": self.network_used,
            "extras": dict(self.extras),
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mock_observation(probe_id: str, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    prompt = (task or {}).get("prompt", "")
    digest = hashlib.sha256(f"{probe_id}:{prompt}".encode("utf-8")).hexdigest()[:12]
    attrs = gate_observation_payload(
        {
            "probe_id": probe_id,
            "quality": capability_figure(0.5, 0),
            "cost": capability_figure(0.0, 0, 0.0),
            "mock": True,
            "mode": "dry-run",
            "task_class": (task or {}).get("task_class"),
            "response_fingerprint": f"mock_{digest}",
            "fleet_redistribute": False,
            "comparative": False,
            "provider": (task or {}).get("provider"),
        }
    )
    return {
        "id": f"urn:mg:observation:mock:{digest}",
        "kind": "Observation",
        "status": "active",
        "valid_start": _now_iso(),
        "valid_end": None,
        "attrs": attrs,
    }


def run_probe(
    probe_id: str,
    *,
    mode: Mode = "dry-run",
    task: dict[str, Any] | None = None,
    allow_network: bool | None = None,
    transport: HttpTransport | None = None,
    limiter: ProviderRateLimiter | None = None,
    token: str | None = None,
) -> ProbeResult:
    """Run a single probe.

    ``mode="dry-run"`` (default) returns a mock Observation and never touches
    the network. ``mode="live"`` requires network permission and an injectable
    or default transport; credentials come from Track M loaders when ``token``
    is omitted.
    """
    if not probe_id:
        raise ValueError("probe_id must be non-empty")

    if mode == "dry-run":
        obs = _mock_observation(probe_id, task=task)
        return ProbeResult(probe_id=probe_id, mode=mode, observation=obs, mock=True, network_used=False)

    if mode != "live":
        raise ValueError(f"unsupported probe mode: {mode!r}")

    permitted = network_allowed() if allow_network is None else bool(allow_network)
    if not permitted:
        raise ProbeNetworkDisabledError(
            f"live probes require {NETWORK_ENV}=1 (defaults OFF); refusing network"
        )

    task = task or {}
    provider = str(task.get("provider") or "").strip().lower()
    model_id = str(task.get("model_id") or task.get("served_id") or "").strip()
    prompt = str(task.get("prompt") or "")
    if not provider or not model_id:
        raise ValueError("live probe requires task.provider and task.model_id/served_id")
    if not prompt:
        raise ValueError("live probe requires task.prompt")

    canary = run_live_canary(
        provider,
        model_id,
        prompt,
        transport=transport,
        token=token,
        limiter=limiter,
        allow_network=True,
    )
    quality_mean = 0.0 if canary.error else 0.6
    obs = build_observation_node(
        probe_id=probe_id,
        model_version_id=str(task.get("model_version_id") or f"urn:mg:modelversion:{provider}:{model_id}"),
        quality=capability_figure(quality_mean, 1),
        cost=capability_figure(0.0, 1, 0.0),
        provider=provider,
        task_class=task.get("task_class"),
        response_fingerprint=canary.fingerprint,
        fleet_redistribute=False,
        comparative=False,
        extra_attrs={
            "mock": False,
            "mode": "live",
            "http_status": canary.status,
            "live_error": canary.error,
        },
    )
    return ProbeResult(
        probe_id=probe_id,
        mode=mode,
        observation=obs,
        mock=False,
        network_used=canary.network_used,
        extras=canary.to_dict(),
    )


__all__ = [
    "NETWORK_ENV",
    "Mode",
    "ProbeNetworkDenied",
    "ProbeNetworkDisabledError",
    "ProbeResult",
    "network_allowed",
    "run_probe",
]
