"""Offline observatory catalog: fixtures → Model / ModelVersion / PriceQuote graph.

Tier 1 Observatory (M2). Loads JSON under fixtures/observatory/ only — no network,
no provider API keys. Cards become priors (capability with n=0); observations later
override cards, never the reverse.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compass.graph import GraphStore, empty_graph
from compass.schema import SCHEMA_ID, GraphDocument

FIXTURES_ENV = "COMPASS_OBSERVATORY_FIXTURES"
CATALOG_SCHEMA = "compass-observatory-catalog/v1"
SOURCES = ("huggingface", "openrouter", "cursor")


def _repo_root() -> Path:
    # src/compass/ingest/catalog.py → parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def default_fixtures_dir() -> Path:
    override = os.environ.get(FIXTURES_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return _repo_root() / "fixtures" / "observatory"


def fixture_path(source: str, *, fixtures_dir: Path | None = None) -> Path:
    src = source.strip().lower()
    if src not in SOURCES:
        raise ValueError(f"unknown observatory source: {source!r}")
    base = fixtures_dir if fixtures_dir is not None else default_fixtures_dir()
    return Path(base) / f"{src}.json"


def load_fixture(source: str, *, path: Path | str | None = None) -> dict[str, Any]:
    """Load one source fixture catalog (JSON). Never performs network I/O."""
    p = Path(path) if path is not None else fixture_path(source)
    if not p.is_file():
        raise FileNotFoundError(f"observatory fixture not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"fixture must be an object: {p}")
    schema = data.get("schema")
    if schema not in (None, CATALOG_SCHEMA):
        raise ValueError(f"unsupported catalog schema: {schema!r}")
    models = data.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError(f"fixture must include a non-empty models list: {p}")
    return data


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip()).strip("-").lower()
    return s or "unknown"


def model_urn(family_or_id: str) -> str:
    return f"urn:mg:model:{_slug(family_or_id)}"


def provider_urn(provider: str) -> str:
    return f"urn:mg:provider:{_slug(provider)}"


def model_version_urn(provider: str, served_id: str) -> str:
    """Stable ModelVersion id from identity (provider, served_id)."""
    digest = hashlib.sha256(f"{provider}|{served_id}".encode("utf-8")).hexdigest()[:12]
    return f"urn:mg:modelversion:{_slug(provider)}:{digest}"


def price_quote_urn(provider: str, served_id: str, *, stamp: str) -> str:
    digest = hashlib.sha256(f"{provider}|{served_id}|{stamp}".encode("utf-8")).hexdigest()[:10]
    return f"urn:mg:pricequote:{_slug(provider)}:{digest}"


def normalize_entry(raw: Mapping[str, Any], *, source: str, card_source: str | None = None) -> dict[str, Any]:
    """Normalize a fixture model row into a common catalog entry."""
    served = raw.get("served_id") or raw.get("id") or raw.get("model_id")
    if not served:
        raise ValueError("catalog entry missing served_id/id")
    provider = str(raw.get("provider") or source)
    family = str(raw.get("model_family") or raw.get("display_name") or served)
    entry = {
        "provider": provider,
        "served_id": str(served),
        "display_name": str(raw.get("display_name") or raw.get("name") or served),
        "model_family": family,
        "context_window": int(raw.get("context_window") or raw.get("contextLength") or 0),
        "tokenizer_id": str(raw.get("tokenizer_id") or "unknown"),
        "price_in_per_mtok": float(raw.get("price_in_per_mtok") or 0.0),
        "price_out_per_mtok": float(raw.get("price_out_per_mtok") or 0.0),
        "currency": str(raw.get("currency") or "USD"),
        "card_source": str(raw.get("card_source") or card_source or f"{source}:fixture"),
        "capability_prior": dict(raw.get("capability_prior") or {}),
    }
    return entry


def entries_from_fixture(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = str(data.get("source") or "unknown")
    card_source = data.get("card_source")
    out: list[dict[str, Any]] = []
    for row in data.get("models") or []:
        if isinstance(row, Mapping):
            out.append(normalize_entry(row, source=source, card_source=card_source if isinstance(card_source, str) else None))
    return out


def _bitemporal(kind: str, node_id: str, *, at: str, label: str | None = None, attrs: dict[str, Any] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id,
        "kind": kind,
        "status": "active",
        "valid_start": at,
        "valid_end": None,
        "attrs": attrs or {},
    }
    if label is not None:
        node["label"] = label
    return node


def _edge(kind: str, edge_id: str, frm: str, to: str, *, at: str, attrs: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": edge_id,
        "kind": kind,
        "from": frm,
        "to": to,
        "status": "active",
        "valid_start": at,
        "valid_end": None,
        "attrs": attrs or {},
    }


def entry_to_graph_fragments(
    entry: Mapping[str, Any],
    *,
    at: str = "2026-09-05T00:00:00Z",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Map one catalog entry to Provider/Model/ModelVersion/PriceQuote + edges."""
    provider = str(entry["provider"])
    served_id = str(entry["served_id"])
    family = str(entry["model_family"])
    p_id = provider_urn(provider)
    m_id = model_urn(family)
    mv_id = model_version_urn(provider, served_id)
    pq_id = price_quote_urn(provider, served_id, stamp=at)

    # Cards = priors only (n=0). Never treat as measured posteriors.
    capability = dict(entry.get("capability_prior") or {})

    nodes = [
        _bitemporal(
            "Provider",
            p_id,
            at=at,
            label=provider,
            attrs={"name": provider, "source": "observatory-fixture"},
        ),
        _bitemporal(
            "Model",
            m_id,
            at=at,
            label=str(entry.get("display_name") or family),
            attrs={"family": family, "display_name": entry.get("display_name")},
        ),
        _bitemporal(
            "ModelVersion",
            mv_id,
            at=at,
            label=f"{served_id}@{at[:10]}",
            attrs={
                "provider": provider,
                "served_id": served_id,
                "model_id": served_id,
                "context_window": entry.get("context_window"),
                "tokenizer_id": entry.get("tokenizer_id"),
                "price_in_per_mtok": entry.get("price_in_per_mtok"),
                "price_out_per_mtok": entry.get("price_out_per_mtok"),
                "card_source": entry.get("card_source"),
                "capability": capability,
            },
        ),
        _bitemporal(
            "PriceQuote",
            pq_id,
            at=at,
            label=f"{served_id} price",
            attrs={
                "provider": provider,
                "served_id": served_id,
                "currency": entry.get("currency") or "USD",
                "price_in_per_mtok": entry.get("price_in_per_mtok"),
                "price_out_per_mtok": entry.get("price_out_per_mtok"),
                "quoted_at": at,
                "card_source": entry.get("card_source"),
            },
        ),
    ]
    edges = [
        _edge("serves", f"urn:mg:edge:serves:{p_id}:{mv_id}", p_id, mv_id, at=at),
        _edge("version_of", f"urn:mg:edge:version_of:{mv_id}:{m_id}", mv_id, m_id, at=at),
        _edge("priced_by", f"urn:mg:edge:priced_by:{pq_id}:{mv_id}", pq_id, mv_id, at=at),
    ]
    return nodes, edges


def merge_fragments(
    doc: GraphDocument,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> GraphDocument:
    """Append nodes/edges, skipping duplicate ids (idempotent re-ingest)."""
    seen_n = {n.get("id") for n in doc.nodes}
    seen_e = {e.get("id") for e in doc.edges}
    for node in nodes:
        nid = node.get("id")
        if nid in seen_n:
            continue
        doc.nodes.append(dict(node))
        seen_n.add(nid)
    for edge in edges:
        eid = edge.get("id")
        if eid in seen_e:
            continue
        doc.edges.append(dict(edge))
        seen_e.add(eid)
    return doc


def build_catalog_document(
    *,
    sources: Iterable[str] = SOURCES,
    fixtures_dir: Path | None = None,
    at: str = "2026-09-05T00:00:00Z",
    entries: Sequence[Mapping[str, Any]] | None = None,
) -> GraphDocument:
    """Build a priced, versioned model-graph document from fixtures (or given entries)."""
    doc = empty_graph()
    if entries is None:
        collected: list[dict[str, Any]] = []
        for source in sources:
            data = load_fixture(source, path=fixture_path(source, fixtures_dir=fixtures_dir))
            collected.extend(entries_from_fixture(data))
        entries = collected
    for entry in entries:
        nodes, edges = entry_to_graph_fragments(entry, at=at)
        merge_fragments(doc, nodes, edges)
    doc.validate()
    return doc


def ingest_fixtures_into_store(
    store: GraphStore,
    *,
    sources: Iterable[str] = SOURCES,
    fixtures_dir: Path | None = None,
    at: str = "2026-09-05T00:00:00Z",
    replace: bool = True,
) -> GraphDocument:
    """Populate GraphStore from offline fixtures. Default replaces the document."""
    built = build_catalog_document(sources=sources, fixtures_dir=fixtures_dir, at=at)
    if replace:
        store.save_document(built)
        return built
    existing = store.load_document(fail_open=True)
    merge_fragments(existing, built.nodes, built.edges)
    existing.validate()
    store.save_document(existing)
    return existing


def list_active_priced_models(
    doc_or_store: GraphDocument | GraphStore,
    *,
    at: str | None = None,
) -> list[dict[str, Any]]:
    """Query helper: active ModelVersions that have an active PriceQuote (priced_by).

    Returns compact dicts suitable for API / Route candidate listing.
    """
    if isinstance(doc_or_store, GraphStore):
        doc = doc_or_store.load_document(fail_open=True)
    else:
        doc = doc_or_store

    versions = doc.active_nodes(kind="ModelVersion", at=at)
    quotes = {n["id"]: n for n in doc.active_nodes(kind="PriceQuote", at=at)}
    priced_targets: dict[str, dict[str, Any]] = {}
    for edge in doc.edges:
        if edge.get("kind") != "priced_by" or edge.get("status") != "active":
            continue
        if at is not None:
            vs, ve = edge.get("valid_start"), edge.get("valid_end")
            if not isinstance(vs, str) or at < vs:
                continue
            if ve is not None and (not isinstance(ve, str) or not (at < ve)):
                continue
        qid, mvid = edge.get("from"), edge.get("to")
        if qid in quotes and isinstance(mvid, str):
            priced_targets[mvid] = quotes[qid]

    out: list[dict[str, Any]] = []
    for mv in versions:
        quote = priced_targets.get(mv["id"])
        if quote is None:
            continue
        attrs = mv.get("attrs") or {}
        qattrs = quote.get("attrs") or {}
        out.append(
            {
                "model_version_id": mv["id"],
                "provider": attrs.get("provider"),
                "served_id": attrs.get("served_id") or attrs.get("model_id"),
                "status": mv.get("status"),
                "valid_start": mv.get("valid_start"),
                "context_window": attrs.get("context_window"),
                "tokenizer_id": attrs.get("tokenizer_id"),
                "card_source": attrs.get("card_source"),
                "price_in_per_mtok": qattrs.get("price_in_per_mtok", attrs.get("price_in_per_mtok")),
                "price_out_per_mtok": qattrs.get("price_out_per_mtok", attrs.get("price_out_per_mtok")),
                "currency": qattrs.get("currency", "USD"),
                "price_quote_id": quote["id"],
            }
        )
    out.sort(key=lambda r: (str(r.get("provider") or ""), str(r.get("served_id") or "")))
    return out
