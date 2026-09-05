"""SDK wrapper — Tier 3 first real enforcement surface.

Thin helper for callers that construct an OpenAI / Cursor-style chat request
with an explicit model field. Extracts prompt text, runs classify+decide, and
returns the chosen model id plus RouteDecision metadata.

Fail-open: any error → configured default model id (never raises to the caller
on the routing path).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, TYPE_CHECKING

from compass.route.decide import RouteConfig, RouteDecisionResult, decide
from compass.route.envelope import BudgetEnvelope
from compass.score.bandit import BanditPosterior

if TYPE_CHECKING:
    from compass.graph import GraphStore

logger = logging.getLogger(__name__)


def extract_prompt_text(chat_request: Mapping[str, Any] | str) -> str:
    """Pull user-facing text from an OpenAI-style chat request or raw string."""
    if isinstance(chat_request, str):
        return chat_request
    messages = chat_request.get("messages")
    if isinstance(messages, list) and messages:
        parts: list[str] = []
        for msg in messages:
            if not isinstance(msg, Mapping):
                continue
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                        parts.append(block["text"])
        if parts:
            return "\n".join(parts)
    for key in ("prompt", "input", "text"):
        val = chat_request.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


@dataclass
class RoutedChat:
    """Chosen model id + full RouteDecision metadata."""

    model: str
    decision: RouteDecisionResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "route_decision": self.decision.to_attrs()
            | {
                "route_decision_id": self.decision.route_decision_id,
                "score": self.decision.score,
            },
        }


def route_chat_request(
    chat_request: Mapping[str, Any] | str,
    *,
    config: RouteConfig | None = None,
    candidates: list[dict[str, Any]] | None = None,
    posterior: BanditPosterior | None = None,
    graph_snapshot: dict[str, Any] | None = None,
    envelope: BudgetEnvelope | dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    store: "GraphStore | None" = None,
) -> RoutedChat:
    """Classify + decide for a chat-shaped request; fail-open to default.

    Returns ``RoutedChat(model=selected_id, decision=...)``. Callers that own
    an SDK client should set ``client.model = result.model`` (or equivalent)
    before issuing the completion.
    """
    cfg = config or RouteConfig()
    try:
        prompt = extract_prompt_text(chat_request)
        decision = decide(
            prompt,
            config=cfg,
            candidates=candidates,
            posterior=posterior,
            graph_snapshot=graph_snapshot,
            envelope=envelope,
            policy=policy,
            store=store,
        )
        return RoutedChat(model=decision.selected_model_version_id, decision=decision)
    except Exception as exc:  # noqa: BLE001 — SDK wrapper fail-open
        logger.exception("route_chat_request fail-open: %s", type(exc).__name__)
        fo = RouteDecisionResult(
            selected_model_version_id=cfg.default_model_version_id,
            task_class_id="general",
            score=0.0,
            lambda_cost=cfg.lambda_cost,
            scores={cfg.default_model_version_id: 0.0},
            rationale=f"fail-open: exception:{type(exc).__name__}",
            fail_open=True,
            default_reason=f"exception:{type(exc).__name__}",
            decided_at="",
            constraints_applied=["sdk:fail_open"],
        )
        return RoutedChat(model=cfg.default_model_version_id, decision=fo)


# Alias matching the plan phrasing "SDK wrapper".
wrap_chat_request = route_chat_request
