"""Cursor model-list ingest — offline fixtures only (Tier 1 Observatory).

Reuses extract_model_ids / resolve_model_ids semantics against a fixture
``models_list`` payload. Does not hardcode machine-specific workspace paths.
No network. No provider API keys.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compass.ingest.catalog import (
    entries_from_fixture,
    fixture_path,
    load_fixture,
    normalize_entry,
)


def extract_model_ids(payload: Any) -> list[str]:
    """Extract model id strings from a Cursor models.list-like payload.

    Accepts:
    - ``{"models": [{"id": ...}, ...]}``
    - ``[{"id": ...}, ...]``
    - ``{"data": [...]}`` (OpenAI-ish wrapper)
    - bare string ids in a list
    """
    models: Any
    if isinstance(payload, Mapping):
        if "models" in payload:
            models = payload.get("models")
        elif "data" in payload:
            models = payload.get("data")
        elif "id" in payload:
            mid = payload.get("id")
            return [str(mid)] if mid else []
        else:
            models = []
    else:
        models = payload

    if not isinstance(models, Sequence) or isinstance(models, (str, bytes)):
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in models:
        mid: str | None = None
        if isinstance(item, str):
            mid = item
        elif isinstance(item, Mapping):
            raw = item.get("id") or item.get("model_id") or item.get("served_id")
            if raw is not None:
                mid = str(raw)
        if mid and mid not in seen:
            seen.add(mid)
            out.append(mid)
    return out


def resolve_model_ids(
    ids: Iterable[str],
    catalog: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Resolve model ids against catalog entries (served_id / id / model_id)."""
    wanted = [str(i) for i in ids]
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in catalog:
        for key in ("served_id", "id", "model_id"):
            val = row.get(key)
            if val is not None:
                by_id.setdefault(str(val), row)
    resolved: list[dict[str, Any]] = []
    for mid in wanted:
        row = by_id.get(mid)
        if row is None:
            continue
        if "provider" in row and ("served_id" in row or "price_in_per_mtok" in row):
            # Already a normalized / rich catalog row
            try:
                resolved.append(normalize_entry(row, source=str(row.get("provider") or "cursor")))
                continue
            except ValueError:
                pass
        # models_list skinny row → normalize with cursor defaults
        enriched = {
            "served_id": mid,
            "display_name": row.get("name") or mid,
            "provider": row.get("provider") or "cursor",
            "context_window": row.get("context_window") or row.get("contextLength") or 0,
            "price_in_per_mtok": (row.get("pricing") or {}).get("input", row.get("price_in_per_mtok", 0.0))
            if isinstance(row.get("pricing"), Mapping)
            else row.get("price_in_per_mtok", 0.0),
            "price_out_per_mtok": (row.get("pricing") or {}).get("output", row.get("price_out_per_mtok", 0.0))
            if isinstance(row.get("pricing"), Mapping)
            else row.get("price_out_per_mtok", 0.0),
            "card_source": "cursor:models.list:fixture",
        }
        resolved.append(normalize_entry(enriched, source="cursor"))
    return resolved


def fetch_catalog(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return normalized Cursor catalog entries from the offline fixture.

    Prefers the rich ``models`` list; if absent, resolves ids from ``models_list``.
    """
    data = load_fixture("cursor", path=path)
    models = data.get("models")
    if isinstance(models, list) and models:
        return entries_from_fixture(data)
    models_list = data.get("models_list") or data
    ids = extract_model_ids(models_list)
    # Fall back: resolve against models_list rows themselves
    rows: list[Mapping[str, Any]] = []
    if isinstance(models_list, Mapping):
        raw_models = models_list.get("models") or models_list.get("data") or []
        if isinstance(raw_models, list):
            rows = [r for r in raw_models if isinstance(r, Mapping)]
    return resolve_model_ids(ids, rows)


def load_raw(path: Path | str | None = None) -> dict[str, Any]:
    """Load the raw Cursor fixture document."""
    return load_fixture("cursor", path=path or fixture_path("cursor"))
