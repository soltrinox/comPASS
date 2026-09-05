"""OpenRouter catalog ingest — offline fixtures + gated live HTTP.

Offline path is default. Live path requires COMPASS_PROBE_ALLOW_NETWORK and
an allowlisted host; credentials via compass.probe.credentials only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compass.ingest.catalog import (
    entries_from_fixture,
    fixture_path,
    load_fixture,
)
from compass.probe.http_transport import HttpTransport
from compass.probe.network_gate import ProbeNetworkDenied, fixture_fallback_reason, network_allowed
from compass.probe.rate_limit import ProviderRateLimiter


def fetch_catalog(
    path: Path | str | None = None,
    *,
    live: bool = False,
    transport: HttpTransport | None = None,
    token: str | None = None,
    limiter: ProviderRateLimiter | None = None,
) -> list[dict[str, Any]]:
    """Return normalized OpenRouter catalog entries.

    Default is offline fixtures. Live mode fail-opens to fixtures when gated.
    """
    if not live:
        data = load_fixture("openrouter", path=path)
        return entries_from_fixture(data)

    if not network_allowed():
        _ = fixture_fallback_reason("openrouter.ai")
        data = load_fixture("openrouter", path=path)
        return entries_from_fixture(data)

    from compass.probe.live_transports import fetch_live_catalog

    try:
        result = fetch_live_catalog(
            "openrouter", transport=transport, token=token, limiter=limiter
        )
        return result.entries or entries_from_fixture(load_fixture("openrouter", path=path))
    except ProbeNetworkDenied:
        data = load_fixture("openrouter", path=path)
        return entries_from_fixture(data)


def load_raw(path: Path | str | None = None) -> dict[str, Any]:
    """Load the raw OpenRouter fixture document."""
    return load_fixture("openrouter", path=path or fixture_path("openrouter"))


__all__ = ["fetch_catalog", "load_raw"]
