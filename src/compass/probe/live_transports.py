"""Live catalog + canary transports for HF / OpenRouter / Cursor.

Native Probe only. Credentials via ``compass.probe.credentials``. All HTTP
goes through ``network_gate`` + injectable ``HttpTransport``. When the gate
denies egress, callers should fall back to offline fixtures (fail-open for
Route consumers of the Observatory snapshot).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import quote

from compass.probe.http_transport import (
    HttpResponse,
    HttpTransport,
    UrlLibHttpTransport,
    auth_headers,
)
from compass.probe.network_gate import (
    PROVIDER_HOSTS,
    ProbeNetworkDenied,
    assert_network_allowed,
    fixture_fallback_reason,
    network_allowed,
)
from compass.probe.rate_limit import DEFAULT_LIMITER, ProviderRateLimiter, RateLimitExceeded
from compass.probe.tos_policy import evaluate_tos

# Canonical live endpoints (hosts must stay on DEFAULT_ALLOWED_HOSTS).
HF_MODELS_URL = "https://huggingface.co/api/models?limit=20&full=true"
HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model_id}"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
CURSOR_MODELS_URL = "https://api2.cursor.sh/aiserver.v1.AiService/AvailableModels"


@dataclass
class CatalogFetchResult:
    provider: str
    entries: list[dict[str, Any]]
    live: bool
    network_used: bool
    fallback_reason: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "entry_count": len(self.entries),
            "live": self.live,
            "network_used": self.network_used,
            "fallback_reason": self.fallback_reason,
        }


@dataclass
class CanaryProbeResult:
    provider: str
    model_id: str
    fingerprint: str
    status: int | None
    mock: bool
    network_used: bool
    error: str | None = None
    body_preview: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "fingerprint": self.fingerprint,
            "status": self.status,
            "mock": self.mock,
            "network_used": self.network_used,
            "error": self.error,
        }


def _default_transport() -> HttpTransport:
    return UrlLibHttpTransport()


def _load_credential(provider: str) -> str | None:
    from compass.probe.credentials import load_provider_credential

    return load_provider_credential(provider)  # type: ignore[arg-type]


def _request(
    transport: HttpTransport,
    provider: str,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout: float | None = 30.0,
    limiter: ProviderRateLimiter | None = None,
) -> HttpResponse:
    assert_network_allowed(url)
    decision = evaluate_tos(provider, for_fleet_redistribute=False, comparative=False)
    if not decision.allowed and decision.reason.startswith("automated"):
        raise ProbeNetworkDenied(decision.reason)
    lim = limiter or DEFAULT_LIMITER
    lim.acquire(provider)
    try:
        resp = transport.request(method, url, headers=headers, body=body, timeout=timeout)
        ok = 200 <= resp.status < 400
        lim.release(provider, success=ok)
        if not ok and resp.status >= 500:
            lim.sleep_backoff(provider)
        return resp
    except Exception:
        lim.release(provider, success=False)
        lim.sleep_backoff(provider)
        raise


def _normalize_hf_models(payload: Any) -> list[dict[str, Any]]:
    rows = payload if isinstance(payload, list) else (payload.get("models") if isinstance(payload, dict) else [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        mid = row.get("id") or row.get("modelId") or row.get("served_id")
        if not mid:
            continue
        out.append(
            {
                "provider": "huggingface",
                "served_id": str(mid),
                "display_name": str(row.get("id") or mid),
                "model_family": str(str(mid).split("/")[0] if "/" in str(mid) else mid),
                "context_window": int(row.get("context_window") or 0),
                "tokenizer_id": "unknown",
                "price_in_per_mtok": float(row.get("price_in_per_mtok") or 0.0),
                "price_out_per_mtok": float(row.get("price_out_per_mtok") or 0.0),
                "currency": "USD",
                "card_source": "huggingface:live",
                "capability_prior": {},
            }
        )
    return out


def _normalize_openrouter_models(payload: Any) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    rows = data if isinstance(data, list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        mid = row.get("id")
        if not mid:
            continue
        pricing = row.get("pricing") if isinstance(row.get("pricing"), Mapping) else {}
        # OpenRouter quotes $ per token; convert to per MTok when tiny.
        pin = float(pricing.get("prompt") or 0.0)
        pout = float(pricing.get("completion") or 0.0)
        if pin < 0.01:
            pin *= 1_000_000
        if pout < 0.01:
            pout *= 1_000_000
        ctx = row.get("context_length") or row.get("context_window") or 0
        out.append(
            {
                "provider": "openrouter",
                "served_id": str(mid),
                "display_name": str(row.get("name") or mid),
                "model_family": str(mid).split("/")[0],
                "context_window": int(ctx or 0),
                "tokenizer_id": "unknown",
                "price_in_per_mtok": pin,
                "price_out_per_mtok": pout,
                "currency": "USD",
                "card_source": "openrouter:live",
                "capability_prior": {},
            }
        )
    return out


def _normalize_cursor_models(payload: Any) -> list[dict[str, Any]]:
    from compass.ingest.cursor import extract_model_ids

    ids = extract_model_ids(payload)
    models = []
    if isinstance(payload, Mapping):
        raw = payload.get("models") or payload.get("data") or []
        if isinstance(raw, list):
            models = [m for m in raw if isinstance(m, Mapping)]
    by_id = {}
    for m in models:
        mid = m.get("id") or m.get("model_id")
        if mid:
            by_id[str(mid)] = m
    out: list[dict[str, Any]] = []
    for mid in ids:
        row = by_id.get(mid, {})
        out.append(
            {
                "provider": "cursor",
                "served_id": mid,
                "display_name": str(row.get("name") or mid),
                "model_family": "cursor",
                "context_window": int(row.get("context_window") or row.get("contextLength") or 0),
                "tokenizer_id": "unknown",
                "price_in_per_mtok": float(row.get("price_in_per_mtok") or 0.0),
                "price_out_per_mtok": float(row.get("price_out_per_mtok") or 0.0),
                "currency": "USD",
                "card_source": "cursor:live",
                "capability_prior": {},
            }
        )
    return out


def fetch_live_catalog(
    provider: str,
    *,
    transport: HttpTransport | None = None,
    token: str | None = None,
    limiter: ProviderRateLimiter | None = None,
    allow_network: bool | None = None,
) -> CatalogFetchResult:
    """Fetch a live provider catalog. Raises ProbeNetworkDenied when gated off."""
    p = provider.strip().lower()
    if p not in PROVIDER_HOSTS:
        raise ValueError(f"unsupported live catalog provider: {provider!r}")
    permitted = network_allowed() if allow_network is None else bool(allow_network)
    if not permitted:
        raise ProbeNetworkDenied(fixture_fallback_reason())

    transport = transport or _default_transport()
    if token is None:
        token = _load_credential(p)

    if p == "huggingface":
        url = HF_MODELS_URL
        resp = _request(
            transport, p, "GET", url, headers=auth_headers(p, token), limiter=limiter
        )
        if resp.status >= 400:
            raise RuntimeError(f"huggingface catalog HTTP {resp.status}")
        entries = _normalize_hf_models(resp.json())
        return CatalogFetchResult(p, entries, True, True, raw={"status": resp.status})

    if p == "openrouter":
        url = OPENROUTER_MODELS_URL
        resp = _request(
            transport, p, "GET", url, headers=auth_headers(p, token), limiter=limiter
        )
        if resp.status >= 400:
            raise RuntimeError(f"openrouter catalog HTTP {resp.status}")
        entries = _normalize_openrouter_models(resp.json())
        return CatalogFetchResult(p, entries, True, True, raw={"status": resp.status})

    # cursor
    url = CURSOR_MODELS_URL
    resp = _request(
        transport, p, "GET", url, headers=auth_headers(p, token), limiter=limiter
    )
    if resp.status >= 400:
        raise RuntimeError(f"cursor catalog HTTP {resp.status}")
    try:
        payload = resp.json()
    except Exception:
        payload = {"models": []}
    entries = _normalize_cursor_models(payload)
    return CatalogFetchResult(p, entries, True, True, raw={"status": resp.status})


def run_live_canary(
    provider: str,
    model_id: str,
    prompt: str,
    *,
    transport: HttpTransport | None = None,
    token: str | None = None,
    limiter: ProviderRateLimiter | None = None,
    allow_network: bool | None = None,
    timeout: float = 30.0,
) -> CanaryProbeResult:
    """Execute one canary prompt against a provider model (native Probe)."""
    p = provider.strip().lower()
    permitted = network_allowed() if allow_network is None else bool(allow_network)
    if not permitted:
        raise ProbeNetworkDenied(fixture_fallback_reason())

    transport = transport or _default_transport()
    if token is None:
        token = _load_credential(p)

    headers = auth_headers(p, token)
    headers = {**headers, "Content-Type": "application/json"}

    if p == "openrouter":
        url = OPENROUTER_CHAT_URL
        body = json.dumps(
            {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
            }
        ).encode("utf-8")
        resp = _request(
            transport, p, "POST", url, headers=headers, body=body, timeout=timeout, limiter=limiter
        )
    elif p == "huggingface":
        url = HF_INFERENCE_URL.format(model_id=quote(model_id, safe="/"))
        body = json.dumps({"inputs": prompt, "parameters": {"max_new_tokens": 64}}).encode("utf-8")
        resp = _request(
            transport, p, "POST", url, headers=headers, body=body, timeout=timeout, limiter=limiter
        )
    elif p == "cursor":
        # Cursor canary uses a chat-completions-shaped endpoint behind the gate.
        url = "https://api2.cursor.sh/chat/completions"
        body = json.dumps(
            {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
            }
        ).encode("utf-8")
        resp = _request(
            transport, p, "POST", url, headers=headers, body=body, timeout=timeout, limiter=limiter
        )
    else:
        raise ValueError(f"unsupported canary provider: {provider!r}")

    preview = resp.text()[:500]
    fp = "fp_" + hashlib.sha256(f"{p}|{model_id}|{prompt}|{resp.status}|{preview}".encode()).hexdigest()[:16]
    err = None if 200 <= resp.status < 400 else f"HTTP {resp.status}"
    return CanaryProbeResult(
        provider=p,
        model_id=model_id,
        fingerprint=fp,
        status=resp.status,
        mock=False,
        network_used=True,
        error=err,
        body_preview=preview,
    )


__all__ = [
    "CURSOR_MODELS_URL",
    "HF_INFERENCE_URL",
    "HF_MODELS_URL",
    "OPENROUTER_CHAT_URL",
    "OPENROUTER_MODELS_URL",
    "CanaryProbeResult",
    "CatalogFetchResult",
    "fetch_live_catalog",
    "run_live_canary",
]
