"""Probe runner — execute bandit-chosen probes (offline / dry-run skeleton).

Holds provider credentials in the Probe process only (future live mode).
Never import this module from route/ or compressor hooks.

Network policy
--------------
* Default mode is **dry-run**: mock Observation payloads, no HTTP.
* Live/network mode requires ``COMPASS_PROBE_ALLOW_NETWORK`` in
  {1, true, yes, on}. The env defaults OFF when unset.
* Even when network is allowed, this offline skeleton does **not** call
  providers (no API keys in repo; live transport not wired). Callers that
  request live execution get ``ProbeNetworkDisabledError`` or
  ``NotImplementedError`` rather than silent egress.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

NETWORK_ENV = "COMPASS_PROBE_ALLOW_NETWORK"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

Mode = Literal["dry-run", "live"]


class ProbeNetworkDisabledError(RuntimeError):
    """Raised when live/network probe execution is requested but egress is OFF."""


@dataclass
class ProbeResult:
    """Offline probe outcome (mock Observation-shaped attrs)."""

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


def network_allowed() -> bool:
    """Return True only when COMPASS_PROBE_ALLOW_NETWORK is explicitly truthy."""
    raw = os.environ.get(NETWORK_ENV, "")
    return raw.strip().lower() in _TRUTHY


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mock_observation(probe_id: str, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    prompt = (task or {}).get("prompt", "")
    digest = hashlib.sha256(f"{probe_id}:{prompt}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"urn:mg:observation:mock:{digest}",
        "kind": "Observation",
        "status": "active",
        "valid_start": _now_iso(),
        "valid_end": None,
        "attrs": {
            "probe_id": probe_id,
            "quality": {"mean": 0.5, "n": 0, "ci95": 1.0},
            "cost": {"mean": 0.0, "n": 0, "ci95": 0.0},
            "mock": True,
            "mode": "dry-run",
            "task_class": (task or {}).get("task_class"),
            "response_fingerprint": f"mock_{digest}",
        },
    }


def run_probe(
    probe_id: str,
    *,
    mode: Mode = "dry-run",
    task: dict[str, Any] | None = None,
    allow_network: bool | None = None,
) -> ProbeResult:
    """Run a single probe.

    ``mode="dry-run"`` (default) returns a mock Observation and never touches
    the network. ``mode="live"`` requires network permission and is not
    implemented in this offline skeleton.
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
    # Offline skeleton: even with the gate open, do not perform real HTTP or
    # read API keys. Live transport lands in a later milestone.
    raise NotImplementedError(
        "live provider probe transport is not wired in the offline daemon skeleton"
    )
