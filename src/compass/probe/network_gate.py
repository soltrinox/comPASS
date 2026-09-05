"""Network egress gate for Probe/Observatory live HTTP.

Locked defaults
---------------
* ``COMPASS_PROBE_ALLOW_NETWORK`` defaults OFF (unset/false → deny).
* Even when the env gate is open, the target host must be on an explicit
  allowlist — no wildcard ``*``.
* Route / core / WASM must never import this module for secret or egress
  decisions; Observatory fail-open serves last-known fixtures when denied.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

NETWORK_ENV = "COMPASS_PROBE_ALLOW_NETWORK"
ALLOWLIST_ENV = "COMPASS_PROBE_HOST_ALLOWLIST"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Explicit hosts only — never a bare "*" wildcard.
DEFAULT_ALLOWED_HOSTS = frozenset(
    {
        "huggingface.co",
        "api-inference.huggingface.co",
        "router.huggingface.co",
        "api.huggingface.co",
        "openrouter.ai",
        "api.openrouter.ai",
        "api2.cursor.sh",
        "api.cursor.com",
        "www.cursor.com",
    }
)

# Canonical catalog / canary endpoints used by live transports.
PROVIDER_HOSTS: dict[str, str] = {
    "huggingface": "huggingface.co",
    "openrouter": "openrouter.ai",
    "cursor": "api2.cursor.sh",
}


class ProbeNetworkDenied(RuntimeError):
    """Raised when live HTTP is requested but the network gate denies it."""


def network_allowed() -> bool:
    """Return True only when COMPASS_PROBE_ALLOW_NETWORK is explicitly truthy."""
    raw = os.environ.get(NETWORK_ENV, "")
    return raw.strip().lower() in _TRUTHY


def configured_allowlist() -> frozenset[str]:
    """Return the active host allowlist (env override or defaults)."""
    raw = os.environ.get(ALLOWLIST_ENV, "").strip()
    if not raw:
        return DEFAULT_ALLOWED_HOSTS
    hosts = {h.strip().lower() for h in raw.split(",") if h.strip()}
    if "*" in hosts:
        raise ProbeNetworkDenied(
            f"{ALLOWLIST_ENV} must not contain wildcard '*'; refusing open egress"
        )
    return frozenset(hosts)


def parse_host(url_or_host: str) -> str:
    """Extract a lowercase hostname from a URL or bare host string."""
    text = (url_or_host or "").strip()
    if not text:
        raise ValueError("url_or_host must be non-empty")
    if "://" not in text:
        # bare host[/path]
        return text.split("/")[0].split(":")[0].lower()
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError(f"could not parse host from {url_or_host!r}")
    return host


def host_allowed(url_or_host: str, *, allowlist: frozenset[str] | None = None) -> bool:
    """True when hostname is on the explicit allowlist (exact or subdomain)."""
    host = parse_host(url_or_host)
    allowed = allowlist if allowlist is not None else configured_allowlist()
    if host in allowed:
        return True
    # Permit subdomains of an allowlisted registrable host (e.g. api.openrouter.ai
    # when openrouter.ai is listed). Still no wildcards.
    for entry in allowed:
        if host.endswith("." + entry):
            return True
    return False


def assert_network_allowed(url_or_host: str, *, allowlist: frozenset[str] | None = None) -> str:
    """Require env gate + allowlisted host. Returns the normalized host.

    Raises ``ProbeNetworkDenied`` (typed deny) when either check fails.
    """
    if not network_allowed():
        raise ProbeNetworkDenied(
            f"live HTTP requires {NETWORK_ENV}=1 (defaults OFF); refusing network"
        )
    host = parse_host(url_or_host)
    if not host_allowed(host, allowlist=allowlist):
        raise ProbeNetworkDenied(
            f"host {host!r} is not on COMPASS Probe allowlist; refusing egress"
        )
    return host


def fixture_fallback_reason(url_or_host: str | None = None) -> str:
    """Human-readable reason for serving last-known fixture snapshot."""
    if not network_allowed():
        return f"{NETWORK_ENV} off — serving fixture snapshot (fail-open)"
    if url_or_host and not host_allowed(url_or_host):
        return f"host not allowlisted — serving fixture snapshot (fail-open)"
    return "network unavailable — serving fixture snapshot (fail-open)"


__all__ = [
    "ALLOWLIST_ENV",
    "DEFAULT_ALLOWED_HOSTS",
    "NETWORK_ENV",
    "PROVIDER_HOSTS",
    "ProbeNetworkDenied",
    "assert_network_allowed",
    "configured_allowlist",
    "fixture_fallback_reason",
    "host_allowed",
    "network_allowed",
    "parse_host",
]
