"""CC-9 advisory file writer (Tier 2 Advisor).

Writes a small ``compass-advisory/v1`` JSON document (and optional markdown
companion) from a RouteDecision so the compressor hook can include a
recommendation line in ``additional_context``.

Fail-open contract (consumer side): missing, stale, or malformed advisory
files MUST be ignored and MUST NOT block Agent Chat. This module never raises
into Agent Chat; write failures are logged and re-raised only when the caller
asks for strict behavior (default: soft — return None on write failure).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

from compass.route.decide import RouteDecisionResult

logger = logging.getLogger(__name__)

ADVISORY_SCHEMA = "compass-advisory/v1"
DEFAULT_TTL_SECONDS = 300  # 5 minutes; matches docs/API.md example window


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_z(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp; return None if malformed."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _decision_as_mapping(decision: RouteDecisionResult | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(decision, RouteDecisionResult):
        attrs = decision.to_attrs()
        attrs["route_decision_id"] = decision.route_decision_id
        attrs["score"] = decision.score
        return attrs
    return dict(decision)


def build_advisory_payload(
    decision: RouteDecisionResult | Mapping[str, Any],
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    model_id: str | None = None,
    provider: str | None = None,
    scores_summary: list[dict[str, Any]] | None = None,
    rationale: str | None = None,
    written_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a ``compass-advisory/v1`` document from a RouteDecision-shaped object.

    Required consumer fields: schema, written_at, expires_at, task_class,
    recommendation.model_id, rationale (optional but preferred).
    """
    attrs = _decision_as_mapping(decision)
    now = written_at or _now_utc()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    ttl = max(1, int(ttl_seconds))
    expires = now + timedelta(seconds=ttl)

    task_class = str(
        attrs.get("task_class")
        or attrs.get("task_class_id")
        or "general"
    )
    model_version_id = str(
        attrs.get("selected_model_version_id")
        or attrs.get("model_version_id")
        or "default"
    )
    mid = model_id or str(attrs.get("model_id") or model_version_id)
    prov = provider or str(attrs.get("provider") or "unknown")

    scores = attrs.get("scores") or {}
    if scores_summary is None:
        scores_summary = []
        if isinstance(scores, Mapping):
            for sid, sval in scores.items():
                entry: dict[str, Any] = {
                    "model_id": str(sid),
                    "score": float(sval) if isinstance(sval, (int, float)) else sval,
                }
                scores_summary.append(entry)
        # Include selected score summary when only aggregate score is known.
        if not scores_summary and "score" in attrs:
            scores_summary = [
                {
                    "model_id": mid,
                    "score": attrs.get("score"),
                    "lambda": attrs.get("lambda"),
                }
            ]

    text_rationale = rationale
    if text_rationale is None:
        text_rationale = str(attrs.get("rationale") or "").strip()
    if not text_rationale:
        n = 0
        if scores_summary:
            n = int(scores_summary[0].get("n") or 0)
        text_rationale = (
            f"this resembles `{task_class}`; selected `{mid}` "
            f"(model_version={model_version_id})"
            + (f" from last {n} tasks of this class" if n else "")
            + "."
        )

    payload: dict[str, Any] = {
        "schema": ADVISORY_SCHEMA,
        "written_at": _iso_z(now),
        "expires_at": _iso_z(expires),
        "task_class": task_class,
        "recommendation": {
            "model_id": mid,
            "provider": prov,
            "model_version_id": model_version_id,
        },
        "rationale": text_rationale,
        "route_decision_id": attrs.get("route_decision_id"),
        "scores_summary": scores_summary,
        "fail_open": bool(attrs.get("fail_open", False)),
        "lambda": attrs.get("lambda"),
    }
    return payload


def format_advisory_markdown(payload: Mapping[str, Any]) -> str:
    """Render a short markdown advisory suitable for session context."""
    rec = payload.get("recommendation") if isinstance(payload.get("recommendation"), Mapping) else {}
    model_id = (rec or {}).get("model_id") or "unknown"
    task_class = payload.get("task_class") or "general"
    rationale = (payload.get("rationale") or "").strip()
    expires = payload.get("expires_at") or ""
    lines = [
        "## comPASS advisory",
        "",
        f"- **task_class:** `{task_class}`",
        f"- **recommended_model:** `{model_id}`",
    ]
    if payload.get("route_decision_id"):
        lines.append(f"- **route_decision_id:** `{payload['route_decision_id']}`")
    if expires:
        lines.append(f"- **expires_at:** `{expires}`")
    scores = payload.get("scores_summary") or []
    if isinstance(scores, list) and scores:
        lines.append("- **scores:**")
        for row in scores[:8]:
            if not isinstance(row, Mapping):
                continue
            mid = row.get("model_id", "?")
            bits = [f"`{mid}`"]
            if "quality_mean" in row:
                bits.append(f"quality={row['quality_mean']}")
            if "score" in row:
                bits.append(f"score={row['score']}")
            if "est_cost_per_task" in row:
                bits.append(f"est_cost={row['est_cost_per_task']}")
            if "n" in row:
                bits.append(f"n={row['n']}")
            lines.append("  - " + ", ".join(str(b) for b in bits))
    if rationale:
        lines.extend(["", rationale])
    lines.append("")
    lines.append("_Advisory only — does not enforce model selection._")
    return "\n".join(lines) + "\n"


def required_fields_present(payload: Any) -> bool:
    """Return True iff payload has the fields consumers require for inclusion."""
    if not isinstance(payload, Mapping):
        return False
    if payload.get("schema") != ADVISORY_SCHEMA:
        return False
    if not payload.get("written_at") or not payload.get("expires_at"):
        return False
    if not payload.get("task_class"):
        return False
    rec = payload.get("recommendation")
    if not isinstance(rec, Mapping) or not rec.get("model_id"):
        return False
    return True


def is_fresh(
    payload: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """Freshness rule from docs/API.md: expires_at in the future + required fields."""
    if not required_fields_present(payload):
        return False
    expires = _parse_iso_z(str(payload.get("expires_at")))
    if expires is None:
        return False
    clock = now or _now_utc()
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    return expires > clock.astimezone(timezone.utc)


def write_advisory(
    path: str | Path,
    decision: RouteDecisionResult | Mapping[str, Any] | None = None,
    *,
    payload: Mapping[str, Any] | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    model_id: str | None = None,
    provider: str | None = None,
    scores_summary: list[dict[str, Any]] | None = None,
    rationale: str | None = None,
    written_at: datetime | None = None,
    write_markdown: bool = True,
    strict: bool = False,
) -> dict[str, Any] | None:
    """Write advisory JSON (and optional ``.md``) to ``path``.

    Pass either ``decision`` (RouteDecisionResult / mapping) or a pre-built
    ``payload``. Returns the written payload, or None on soft failure.
    """
    dest = Path(path)
    try:
        if payload is None:
            if decision is None:
                raise ValueError("write_advisory requires decision or payload")
            doc = build_advisory_payload(
                decision,
                ttl_seconds=ttl_seconds,
                model_id=model_id,
                provider=provider,
                scores_summary=scores_summary,
                rationale=rationale,
                written_at=written_at,
            )
        else:
            doc = dict(payload)
            # Ensure freshness timestamps exist when caller supplies a partial payload.
            if "written_at" not in doc or "expires_at" not in doc:
                base = build_advisory_payload(
                    decision or doc,
                    ttl_seconds=ttl_seconds,
                    model_id=model_id,
                    provider=provider,
                    scores_summary=scores_summary,
                    rationale=rationale,
                    written_at=written_at,
                )
                for key in ("schema", "written_at", "expires_at", "task_class", "recommendation"):
                    doc.setdefault(key, base[key])
                doc.setdefault("rationale", base.get("rationale"))
                doc.setdefault("scores_summary", base.get("scores_summary"))

        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        tmp.replace(dest)

        if write_markdown:
            md_path = dest.with_suffix(".md") if dest.suffix.lower() == ".json" else Path(str(dest) + ".md")
            md_tmp = md_path.with_suffix(md_path.suffix + ".tmp")
            md_tmp.write_text(format_advisory_markdown(doc), encoding="utf-8")
            md_tmp.replace(md_path)

        return doc
    except Exception as exc:  # noqa: BLE001 — fail-open for callers that soft-write
        logger.debug("advisory write failed path=%s err=%r", dest, exc)
        if strict:
            raise
        return None


# Back-compat alias used by early stubs / docs.
def write_advisory_file(path: str | Path, payload: Mapping[str, Any], **kwargs: Any) -> dict[str, Any] | None:
    return write_advisory(path, payload=payload, **kwargs)
