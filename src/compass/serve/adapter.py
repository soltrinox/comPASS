"""Generic LLM adapter — decide / catalog pin / proxy override (ADR 0006).

Normative contract: ``docs/API.md`` §6.

Priority: proxy_override > catalog > decide.
Strips ``compass`` from outbound bodies. Optional comPREssOR hop hook.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from compass.route.decide import RouteConfig, RouteDecisionResult, decide
from compass.route.envelope import BudgetEnvelope
from compass.serve.sdk import extract_prompt_text, route_chat_request

logger = logging.getLogger(__name__)

MODE_DECIDE = "decide"
MODE_CATALOG = "catalog"
MODE_PROXY = "proxy_override"

CompressHook = Callable[[dict[str, Any], "AdapterResult"], dict[str, Any]]


@dataclass
class AdapterConfig:
    """Runtime knobs shared with the proxy/serve plane."""

    route_config: RouteConfig = field(default_factory=RouteConfig)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    envelope: BudgetEnvelope | dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    store: Any | None = None
    default_upstream: str | None = None
    """Fallback base URL when catalog/decide entry has no upstream (legacy COMPASS_PROXY_UPSTREAM)."""
    host_allowlist: list[str] | None = None
    """If set, proxy_override hosts must match (exact or trailing-domain). None = allow all (native/tests)."""
    previous_model: str | None = None
    compress_hook: CompressHook | None = None
    default_candidates: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"id": "cheap-local", "quality": 0.7, "cost": 0.05, "upstream": None},
            {"id": "strong-local", "quality": 0.9, "cost": 0.4, "upstream": None},
        ]
    )

    def resolved_candidates(self) -> list[dict[str, Any]]:
        return list(self.candidates or self.default_candidates)


@dataclass
class AdapterResult:
    """Resolved routing + outbound chat body (``compass`` stripped)."""

    selection_mode: str
    model: str
    decision: RouteDecisionResult
    outbound_body: dict[str, Any]
    upstream_url: str | None
    """Full chat-completions URL, or None for dry-run."""
    compressed: bool = False
    denied: bool = False
    deny_reason: str | None = None


def strip_compass(body: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow copy without the ``compass`` extension key."""
    out = dict(body)
    out.pop("compass", None)
    return out


def build_target_url(compass: Mapping[str, Any]) -> str | None:
    """Build absolute completions URL from ``target_url`` or ``target`` object."""
    raw = compass.get("target_url")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().rstrip("/")

    target = compass.get("target")
    if not isinstance(target, Mapping):
        return None
    host = target.get("host")
    if not host or not isinstance(host, str):
        return None
    scheme = str(target.get("scheme") or "https").lower()
    port = target.get("port")
    path = str(target.get("path") or "/v1/chat/completions")
    if not path.startswith("/"):
        path = "/" + path
    if port is None:
        netloc = host
    else:
        netloc = f"{host}:{int(port)}"
    return f"{scheme}://{netloc}{path}"


def host_allowed(url: str, allowlist: list[str] | None) -> bool:
    """Deny-by-default when allowlist is a non-empty list; None means unrestricted."""
    if allowlist is None:
        return True
    if not allowlist:
        return False
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    for entry in allowlist:
        e = entry.lower().lstrip(".")
        if host == e or host.endswith("." + e):
            return True
    return False


def _candidate_id(cand: Mapping[str, Any]) -> str:
    return str(cand.get("id") or cand.get("model_version_id") or "")


def find_catalog_entry(
    candidates: list[dict[str, Any]],
    *,
    model_version_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    """Match Graph/catalog candidate by URN or served id / alias."""
    for cand in candidates:
        cid = _candidate_id(cand)
        aliases = {
            cid,
            str(cand.get("served_id") or ""),
            str(cand.get("model") or ""),
            str(cand.get("alias") or ""),
        }
        aliases.discard("")
        if model_version_id and (
            model_version_id == cid or model_version_id in aliases
        ):
            return cand
        if model and model in aliases:
            return cand
    return None


def upstream_for_candidate(
    cand: Mapping[str, Any] | None,
    *,
    default_upstream: str | None,
    path: str = "/v1/chat/completions",
) -> str | None:
    """Resolve full completions URL from candidate attrs or default base."""
    if cand:
        for key in ("completions_url", "target_url"):
            val = cand.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        base = cand.get("upstream") or cand.get("base_url")
        if isinstance(base, str) and base.strip():
            b = base.strip().rstrip("/")
            if b.endswith("/v1/chat/completions"):
                return b
            return f"{b}{path}"
    if default_upstream:
        b = default_upstream.strip().rstrip("/")
        if b.endswith("/v1/chat/completions"):
            return b
        return f"{b}/v1/chat/completions"
    return None


def _pin_decision(
    *,
    model: str,
    mode: str,
    config: AdapterConfig,
    rationale: str,
    fail_open: bool = False,
    default_reason: str | None = None,
    compass: Mapping[str, Any] | None = None,
) -> RouteDecisionResult:
    cfg = config.route_config or RouteConfig()
    compass = compass or {}
    result = RouteDecisionResult(
        selected_model_version_id=model,
        task_class_id="general",
        score=0.0,
        lambda_cost=cfg.lambda_cost,
        scores={model: 0.0},
        rationale=rationale,
        fail_open=fail_open,
        default_reason=default_reason,
        decided_at="",
        constraints_applied=[f"adapter:{mode}"],
        selection_mode=mode,
        trajectory_id=compass.get("trajectory_id")
        if isinstance(compass.get("trajectory_id"), str)
        else None,
        episode_id=compass.get("session_id")
        if isinstance(compass.get("session_id"), str)
        else None,
    )
    store = config.store
    if store is not None:
        try:
            from compass.route.decide import _persist_decision

            return _persist_decision(result, store)
        except Exception:  # noqa: BLE001
            logger.exception("adapter persist failed")
    return result


def default_compress_hook(body: dict[str, Any], result: AdapterResult) -> dict[str, Any]:
    """Lightweight seam for comPREssOR hop-safe forward injection.

    Marks the outbound body with a system preamble when hopping; real
    compression should replace this hook with comPREssOR.
    """
    messages = list(body.get("messages") or [])
    note = (
        "[comPASS hop] context forwarded for cross-model continuity "
        f"(selection_mode={result.selection_mode}; model={result.model}). "
        "Replace this hook with comPREssOR hop-safe injection in production."
    )
    messages = [{"role": "system", "content": note}, *messages]
    out = dict(body)
    out["messages"] = messages
    return out


def adapt_chat_completions(
    body: Mapping[str, Any],
    *,
    config: AdapterConfig | None = None,
) -> AdapterResult:
    """Resolve selection mode, build outbound body, choose upstream URL."""
    cfg = config or AdapterConfig()
    raw = dict(body)
    compass = raw.get("compass") if isinstance(raw.get("compass"), Mapping) else {}
    compass = dict(compass)
    candidates = cfg.resolved_candidates()
    path_default = "/v1/chat/completions"

    # --- 1) proxy override ---
    target_url = build_target_url(compass)
    if target_url:
        override_model = None
        t = compass.get("target")
        if isinstance(t, Mapping) and t.get("model"):
            override_model = str(t["model"])
        model = override_model or str(raw.get("model") or "override")
        if not host_allowed(target_url, cfg.host_allowlist):
            decision = _pin_decision(
                model=model,
                mode=MODE_PROXY,
                config=cfg,
                rationale="proxy_override denied: host not allowlisted",
                fail_open=True,
                default_reason="proxy_host_denied",
                compass=compass,
            )
            outbound = strip_compass(raw)
            outbound["model"] = model
            return AdapterResult(
                selection_mode=MODE_PROXY,
                model=model,
                decision=decision,
                outbound_body=outbound,
                upstream_url=None,
                denied=True,
                deny_reason="proxy_host_denied",
            )
        decision = _pin_decision(
            model=model,
            mode=MODE_PROXY,
            config=cfg,
            rationale=f"proxy_override → {target_url}",
            compass=compass,
        )
        outbound = strip_compass(raw)
        outbound["model"] = model
        result = AdapterResult(
            selection_mode=MODE_PROXY,
            model=model,
            decision=decision,
            outbound_body=outbound,
            upstream_url=target_url,
        )
        return _maybe_compress(raw, result, cfg, compass)

    # --- 2) catalog pin ---
    pin_id = compass.get("model_version_id")
    pin_id = str(pin_id) if isinstance(pin_id, str) and pin_id.strip() else None
    top_model = raw.get("model")
    top_model = str(top_model) if isinstance(top_model, str) and top_model.strip() else None
    # Treat placeholder / ignored models as non-pins (legacy proxy tests use model=ignored)
    ignored = {"ignored", "auto", "compass", "compass-auto", ""}
    catalog_model = None if (top_model and top_model.lower() in ignored) else top_model
    entry = None
    if pin_id:
        entry = find_catalog_entry(candidates, model_version_id=pin_id)
    if entry is None and catalog_model:
        entry = find_catalog_entry(candidates, model=catalog_model)

    if entry is not None and (pin_id or catalog_model):
        model = _candidate_id(entry)
        upstream = upstream_for_candidate(
            entry, default_upstream=cfg.default_upstream, path=path_default
        )
        decision = _pin_decision(
            model=model,
            mode=MODE_CATALOG,
            config=cfg,
            rationale=f"catalog pin → {model}",
            compass=compass,
        )
        outbound = strip_compass(raw)
        outbound["model"] = model
        result = AdapterResult(
            selection_mode=MODE_CATALOG,
            model=model,
            decision=decision,
            outbound_body=outbound,
            upstream_url=upstream,
        )
        return _maybe_compress(raw, result, cfg, compass)

    if pin_id and entry is None:
        # Explicit pin miss — fail-open to default unless fallback handled by decide
        if compass.get("fallback_to_decide"):
            pass  # fall through to decide
        else:
            fo = (cfg.route_config or RouteConfig()).default_model_version_id
            decision = _pin_decision(
                model=fo,
                mode=MODE_CATALOG,
                config=cfg,
                rationale=f"catalog pin miss for {pin_id}; fail-open",
                fail_open=True,
                default_reason="catalog_miss",
                compass=compass,
            )
            outbound = strip_compass(raw)
            outbound["model"] = fo
            upstream = upstream_for_candidate(
                None, default_upstream=cfg.default_upstream
            )
            return AdapterResult(
                selection_mode=MODE_CATALOG,
                model=fo,
                decision=decision,
                outbound_body=outbound,
                upstream_url=upstream,
            )

    # --- 3) decide ---
    routed = route_chat_request(
        raw,
        config=cfg.route_config,
        candidates=candidates,
        envelope=cfg.envelope,
        policy=cfg.policy,
        store=cfg.store,
    )
    decision = routed.decision
    decision.selection_mode = MODE_DECIDE
    # Re-persist attrs if store already wrote without selection_mode — best-effort
    model = routed.model
    entry = find_catalog_entry(candidates, model_version_id=model, model=model)
    upstream = upstream_for_candidate(
        entry, default_upstream=cfg.default_upstream, path=path_default
    )
    outbound = strip_compass(raw)
    outbound["model"] = model
    if isinstance(compass.get("trajectory_id"), str):
        decision.trajectory_id = decision.trajectory_id or compass["trajectory_id"]
    result = AdapterResult(
        selection_mode=MODE_DECIDE,
        model=model,
        decision=decision,
        outbound_body=outbound,
        upstream_url=upstream,
    )
    return _maybe_compress(raw, result, cfg, compass)


def _maybe_compress(
    original: Mapping[str, Any],
    result: AdapterResult,
    cfg: AdapterConfig,
    compass: Mapping[str, Any],
) -> AdapterResult:
    compress = compass.get("compress") if isinstance(compass.get("compress"), Mapping) else {}
    hop = bool(compress.get("hop")) if compress else False
    enabled = compress.get("enabled", True) if compress else True
    prev = cfg.previous_model
    should = bool(enabled) and (
        hop or (prev is not None and prev != result.model)
    )
    if not should:
        return result
    hook = cfg.compress_hook or default_compress_hook
    try:
        result.outbound_body = hook(result.outbound_body, result)
        result.compressed = True
    except Exception:  # noqa: BLE001
        logger.exception("compress hook failed — continuing without inject")
    return result


def proxy_config_to_adapter(config: Any) -> AdapterConfig:
    """Map ``ProxyConfig`` (or compatible) onto ``AdapterConfig``."""
    from compass.serve.proxy import ProxyConfig

    if isinstance(config, AdapterConfig):
        return config
    if not isinstance(config, ProxyConfig):
        return AdapterConfig()
    return AdapterConfig(
        route_config=config.route_config,
        candidates=list(config.candidates),
        envelope=config.envelope,
        policy=config.policy,
        store=config.store,
        default_upstream=config.upstream,
        host_allowlist=getattr(config, "host_allowlist", None),
        previous_model=getattr(config, "previous_model", None),
        compress_hook=getattr(config, "compress_hook", None),
        default_candidates=list(config.default_candidates),
    )
