"""OpenAI-compatible local proxy (Tier 3 enforcement).

Accepts POST /v1/chat/completions-shaped JSON, runs ``decide()``, then:

* **Dry-run (default):** when ``COMPASS_PROXY_UPSTREAM`` is unset, return a
  JSON body showing which model *would* be used — no upstream call, no API
  keys required.
* **Forward:** when ``COMPASS_PROXY_UPSTREAM`` is set to a base URL, rewrite
  ``model`` to the routed choice and POST the body to
  ``{upstream}/v1/chat/completions``.

Never requires real provider keys for tests. Credentials (if any) belong in
this process only — never on the hook path.

Run dry-run locally::

    python -m compass.serve.proxy --port 8787
    curl -s localhost:8787/v1/chat/completions \
      -H 'content-type: application/json' \
      -d '{"model":"ignored","messages":[{"role":"user","content":"fix a bug"}]}'
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

from compass.route.decide import RouteConfig, RouteDecisionResult
from compass.route.envelope import BudgetEnvelope
from compass.serve.sdk import route_chat_request

logger = logging.getLogger(__name__)

ENV_UPSTREAM = "COMPASS_PROXY_UPSTREAM"
ENV_HOST = "COMPASS_PROXY_HOST"
ENV_PORT = "COMPASS_PROXY_PORT"


@dataclass
class ProxyConfig:
    """Runtime knobs for the local proxy (no secrets required for dry-run)."""

    upstream: str | None = None
    route_config: RouteConfig = field(default_factory=RouteConfig)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    envelope: BudgetEnvelope | dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    store: Any | None = None  # GraphStore | None; typed loosely to avoid import cycle
    default_candidates: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"id": "cheap-local", "quality": 0.7, "cost": 0.05},
            {"id": "strong-local", "quality": 0.9, "cost": 0.4},
        ]
    )

    def resolved_candidates(self) -> list[dict[str, Any]]:
        return list(self.candidates or self.default_candidates)

    @classmethod
    def from_env(cls, **overrides: Any) -> "ProxyConfig":
        upstream = overrides.pop("upstream", None)
        if upstream is None:
            raw = os.environ.get(ENV_UPSTREAM, "").strip()
            upstream = raw or None
        return cls(upstream=upstream, **overrides)


def _decision_payload(decision: RouteDecisionResult) -> dict[str, Any]:
    return decision.to_attrs() | {
        "route_decision_id": decision.route_decision_id,
        "score": decision.score,
    }


def route_completion_body(
    body: dict[str, Any],
    *,
    config: ProxyConfig | None = None,
) -> tuple[str, RouteDecisionResult, dict[str, Any]]:
    """Run routing on a chat-completions body; return (model, decision, outbound_body)."""
    cfg = config or ProxyConfig.from_env()
    routed = route_chat_request(
        body,
        config=cfg.route_config,
        candidates=cfg.resolved_candidates(),
        envelope=cfg.envelope,
        policy=cfg.policy,
        store=cfg.store,
    )
    outbound = dict(body)
    outbound["model"] = routed.model
    return routed.model, routed.decision, outbound


def dry_run_response(
    model: str,
    decision: RouteDecisionResult,
    *,
    original_model: Any = None,
) -> dict[str, Any]:
    """OpenAI-shaped stub that reports the routed model without forwarding."""
    return {
        "id": f"compass-dry-run-{decision.route_decision_id or 'local'}",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        f"[comPASS dry-run] would route to model={model!r} "
                        f"(original_model={original_model!r}, "
                        f"task_class={decision.task_class_id!r}, "
                        f"fail_open={decision.fail_open})"
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "compass": {
            "dry_run": True,
            "upstream": None,
            "selected_model": model,
            "original_model": original_model,
            "route_decision": _decision_payload(decision),
        },
    }


def forward_upstream(
    upstream: str,
    outbound_body: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, str], bytes]:
    """POST outbound_body to ``{upstream}/v1/chat/completions``.

    Returns (status, response_headers, raw_body). Raises on transport errors.
    """
    base = upstream.rstrip("/")
    url = f"{base}/v1/chat/completions"
    data = json.dumps(outbound_body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        # Do not forward hop-by-hop; allow Authorization through for real keys.
        for k, v in headers.items():
            lk = k.lower()
            if lk in {"host", "content-length", "transfer-encoding", "connection"}:
                continue
            req_headers[k] = v
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — operator-set URL
        raw = resp.read()
        resp_headers = {k: v for k, v in resp.headers.items()}
        return int(resp.status), resp_headers, raw


def handle_chat_completions(
    body: dict[str, Any],
    *,
    config: ProxyConfig | None = None,
    inbound_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any] | bytes, str]:
    """Core handler: decide → dry-run JSON or upstream forward.

    Returns (http_status, payload, content_type). Payload is dict for dry-run
    / error JSON, or raw bytes when forwarding upstream.
    """
    cfg = config or ProxyConfig.from_env()
    try:
        model, decision, outbound = route_completion_body(body, config=cfg)
    except Exception as exc:  # noqa: BLE001
        logger.exception("proxy routing failed")
        fo_model = (cfg.route_config or RouteConfig()).default_model_version_id
        err = {
            "error": {
                "message": f"routing failed open to {fo_model}: {type(exc).__name__}",
                "type": "compass_route_error",
            },
            "compass": {"dry_run": True, "selected_model": fo_model, "fail_open": True},
        }
        return 200, err, "application/json"

    if not cfg.upstream:
        return (
            200,
            dry_run_response(model, decision, original_model=body.get("model")),
            "application/json",
        )

    try:
        status, _hdrs, raw = forward_upstream(
            cfg.upstream, outbound, headers=inbound_headers
        )
        return status, raw, "application/json"
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else str(exc).encode()
        return int(exc.code), raw, "application/json"
    except Exception as exc:  # noqa: BLE001 — still fail-open with dry-run info
        logger.exception("upstream forward failed; returning dry-run")
        payload = dry_run_response(model, decision, original_model=body.get("model"))
        payload["compass"]["upstream_error"] = type(exc).__name__
        payload["compass"]["upstream"] = cfg.upstream
        return 200, payload, "application/json"


# ---------------------------------------------------------------------------
# Minimal ASGI app (stdlib — no Starlette/FastAPI required)
# ---------------------------------------------------------------------------

async def _read_body(receive: Callable) -> bytes:
    chunks: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            continue
        chunks.append(message.get("body", b""))
        if not message.get("more_body"):
            break
    return b"".join(chunks)


def create_asgi_app(config: ProxyConfig | None = None) -> Callable:
    """Return an ASGI callable for httpx ASGITransport / uvicorn / etc."""

    cfg = config or ProxyConfig.from_env()

    async def app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            return
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        if method == "GET" and path in {"/", "/healthz", "/health"}:
            body = json.dumps({"ok": True, "dry_run": not bool(cfg.upstream)}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        if method != "POST" or path.rstrip("/") != "/v1/chat/completions":
            body = json.dumps({"error": {"message": "not found", "type": "not_found"}}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        raw_in = await _read_body(receive)
        try:
            payload = json.loads(raw_in.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("body must be a JSON object")
        except (ValueError, UnicodeDecodeError) as exc:
            err = json.dumps({"error": {"message": str(exc), "type": "invalid_request"}}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": err})
            return

        headers = {
            k.decode("latin1"): v.decode("latin1")
            for k, v in scope.get("headers", [])
        }
        status, out, ctype = handle_chat_completions(
            payload, config=cfg, inbound_headers=headers
        )
        if isinstance(out, (bytes, bytearray)):
            raw_out = bytes(out)
        else:
            raw_out = json.dumps(out).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", ctype.encode("ascii"))],
            }
        )
        await send({"type": "http.response.body", "body": raw_out})

    return app


# ---------------------------------------------------------------------------
# stdlib http.server
# ---------------------------------------------------------------------------

def make_handler(config: ProxyConfig) -> type[BaseHTTPRequestHandler]:
    class ProxyHandler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/healthz", "/health"}:
                body = json.dumps(
                    {"ok": True, "dry_run": not bool(config.upstream)}
                ).encode()
                self._send(200, body)
                return
            self._send(
                404,
                json.dumps({"error": {"message": "not found", "type": "not_found"}}).encode(),
            )

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path.rstrip("/")
            if path != "/v1/chat/completions":
                self._send(
                    404,
                    json.dumps({"error": {"message": "not found", "type": "not_found"}}).encode(),
                )
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("body must be a JSON object")
            except (ValueError, UnicodeDecodeError) as exc:
                self._send(
                    400,
                    json.dumps(
                        {"error": {"message": str(exc), "type": "invalid_request"}}
                    ).encode(),
                )
                return
            inbound = {k: v for k, v in self.headers.items()}
            status, out, ctype = handle_chat_completions(
                payload, config=config, inbound_headers=inbound
            )
            if isinstance(out, (bytes, bytearray)):
                raw_out = bytes(out)
            else:
                raw_out = json.dumps(out).encode("utf-8")
            self._send(status, raw_out, ctype)

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.info("%s - %s", self.address_string(), fmt % args)

    return ProxyHandler


def serve_forever(
    host: str = "127.0.0.1",
    port: int = 8787,
    config: ProxyConfig | None = None,
) -> ThreadingHTTPServer:
    """Bind ThreadingHTTPServer and block until KeyboardInterrupt."""
    cfg = config or ProxyConfig.from_env()
    handler = make_handler(cfg)
    httpd = ThreadingHTTPServer((host, port), handler)
    mode = f"upstream={cfg.upstream}" if cfg.upstream else "dry-run"
    logger.info("comPASS proxy listening on http://%s:%s (%s)", host, port, mode)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("proxy shutting down")
    finally:
        httpd.server_close()
    return httpd


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="comPASS OpenAI-compatible proxy (Tier 3)")
    parser.add_argument("--host", default=os.environ.get(ENV_HOST, "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get(ENV_PORT, "8787")),
    )
    parser.add_argument(
        "--upstream",
        default=None,
        help=f"Upstream base URL (or set {ENV_UPSTREAM}). Default: dry-run only.",
    )
    args = parser.parse_args(argv)
    cfg = ProxyConfig.from_env(upstream=args.upstream)
    print(
        f"comPASS proxy on http://{args.host}:{args.port} "
        f"({'forward → ' + cfg.upstream if cfg.upstream else 'dry-run only'})",
        flush=True,
    )
    serve_forever(host=args.host, port=args.port, config=cfg)


if __name__ == "__main__":
    main()
