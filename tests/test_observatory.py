"""Tier 1 Observatory: fixture ingest, priced catalog, fingerprint supersession (M2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass.graph import GraphStore, GraphStoreConfig
from compass.ingest import (
    SOURCES,
    build_catalog_document,
    cursor,
    huggingface,
    ingest_fixtures_into_store,
    list_active_priced_models,
    openrouter,
)
from compass.ingest.catalog import (
    entries_from_fixture,
    entry_to_graph_fragments,
    load_fixture,
    model_version_urn,
)
from compass.probe.canary import load_canary_set, run_canaries
from compass.schema import SCHEMA_ID

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "fixtures" / "observatory"
CANARY = REPO_ROOT / "fixtures" / "probe" / "canary_set.json"
M2_DIR = REPO_ROOT / "test-results" / "m2-observatory"


def test_fixtures_exist_for_all_sources():
    for source in SOURCES:
        path = FIXTURES / f"{source}.json"
        assert path.is_file(), path
        data = load_fixture(source, path=path)
        assert data["schema"] == "compass-observatory-catalog/v1"
        assert entries_from_fixture(data)


def test_huggingface_and_openrouter_fetch_offline():
    hf = huggingface.fetch_catalog()
    or_ = openrouter.fetch_catalog()
    assert len(hf) >= 2
    assert len(or_) >= 2
    assert all(e["provider"] == "huggingface" for e in hf)
    assert all(e["provider"] == "openrouter" for e in or_)
    assert all("price_in_per_mtok" in e for e in hf + or_)


def test_cursor_extract_and_resolve_model_ids():
    raw = cursor.load_raw()
    ids = cursor.extract_model_ids(raw["models_list"])
    assert "cursor-grok-4.6-high-fast" in ids
    assert "cursor-composer-1" in ids
    resolved = cursor.resolve_model_ids(ids, raw["models"])
    assert len(resolved) == 2
    assert {r["served_id"] for r in resolved} == set(ids)
    # fetch_catalog uses rich models list
    catalog = cursor.fetch_catalog()
    assert len(catalog) == 2


def test_build_catalog_document_priced_and_versioned():
    doc = build_catalog_document(at="2026-09-05T00:00:00Z")
    assert doc.schema == SCHEMA_ID
    versions = doc.active_nodes(kind="ModelVersion")
    models = doc.active_nodes(kind="Model")
    quotes = doc.active_nodes(kind="PriceQuote")
    providers = doc.active_nodes(kind="Provider")
    assert len(versions) >= 6  # 2 per source × 3 sources
    assert len(models) >= 1
    assert len(quotes) == len(versions)
    assert len(providers) == 3
    # Identity (provider, served_id) present on every version
    for mv in versions:
        attrs = mv["attrs"]
        assert attrs.get("provider")
        assert attrs.get("served_id")
        assert attrs.get("card_source")
        # Card priors only (n=0) when present
        for fig in (attrs.get("capability") or {}).values():
            assert fig.get("n") == 0
    # Edges: serves, version_of, priced_by
    kinds = {e["kind"] for e in doc.edges}
    assert {"serves", "version_of", "priced_by"} <= kinds
    priced = list_active_priced_models(doc)
    assert len(priced) == len(versions)
    assert all(p["price_quote_id"] for p in priced)


def test_ingest_into_graph_store(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "obs")
    with GraphStore(cfg) as store:
        doc = ingest_fixtures_into_store(store, sources=("huggingface", "openrouter"))
        assert len(doc.active_nodes(kind="ModelVersion")) >= 4
        reloaded = store.load_document(fail_open=False)
        priced = list_active_priced_models(store)
        assert len(priced) >= 4
        assert len(reloaded.active_nodes(kind="PriceQuote")) >= 4


def test_entry_fragments_stable_urns():
    entry = {
        "provider": "openrouter",
        "served_id": "openai/gpt-4.1-mini",
        "display_name": "GPT-4.1 Mini",
        "model_family": "gpt-4.1-mini",
        "context_window": 1000,
        "tokenizer_id": "o200k_base",
        "price_in_per_mtok": 0.4,
        "price_out_per_mtok": 1.6,
        "currency": "USD",
        "card_source": "openrouter:fixture",
        "capability_prior": {},
    }
    nodes1, _ = entry_to_graph_fragments(entry, at="2026-09-05T00:00:00Z")
    nodes2, _ = entry_to_graph_fragments(entry, at="2026-09-05T00:00:00Z")
    assert model_version_urn("openrouter", "openai/gpt-4.1-mini") == nodes1[2]["id"]
    assert {n["id"] for n in nodes1} == {n["id"] for n in nodes2}


def test_observatory_fingerprint_change_supersedes_not_overwrite(tmp_path: Path):
    """M2 exit: priced catalog + induced fingerprint → supersede (not score overwrite)."""
    cfg = GraphStoreConfig(root=tmp_path / "m2")
    with GraphStore(cfg) as store:
        doc = ingest_fixtures_into_store(store)
        versions = doc.active_nodes(kind="ModelVersion")
        assert versions
        target = versions[0]
        old_id = target["id"]
        # Attach a measured posterior (simulating probe history) on the active version.
        target.setdefault("attrs", {})["capability"] = {
            "code_generation": {"mean": 0.82, "n": 40, "ci95": 0.05}
        }
        target["attrs"]["drift_fingerprint"] = "cn_baseline_observatory"
        store.save_document(doc)

        def shifted_fp(model_version_id: str, canary: dict) -> str:
            return f"obs-shift|{model_version_id}|{canary['id']}"

        results = run_canaries(
            doc,
            model_version_ids=[old_id],
            canaries=load_canary_set(CANARY),
            get_fingerprint=shifted_fp,
            at="2026-09-05T12:00:00Z",
        )
        assert results[0]["changed"] is True
        assert results[0]["superseded"] is True
        new_id = results[0]["new_model_version_id"]
        assert new_id and new_id != old_id

        old = doc.node_by_id(old_id)
        new = doc.node_by_id(new_id)
        assert old is not None and new is not None
        assert old["status"] == "superseded"
        assert old["valid_end"] == "2026-09-05T12:00:00Z"
        # Prior scores remain on superseded node — not overwritten / not carried forward.
        assert old["attrs"]["capability"]["code_generation"]["mean"] == 0.82
        assert "capability" not in new["attrs"]
        assert new["status"] == "active"
        assert new["attrs"]["drift_fingerprint"] != "cn_baseline_observatory"
        supersedes = [e for e in doc.edges if e["kind"] == "supersedes"]
        assert any(e["to"] == old_id and e["from"] == new_id for e in supersedes)

        store.save_document(doc)
        # Active priced listing excludes superseded versions
        active_ids = {p["model_version_id"] for p in list_active_priced_models(store)}
        assert old_id not in active_ids

        # M2 evidence artifact
        M2_DIR.mkdir(parents=True, exist_ok=True)
        evidence = {
            "milestone": "M2",
            "catalog_active_model_versions_before_drift": len(versions),
            "priced_active_before": len(list_active_priced_models(build_catalog_document())),
            "superseded_id": old_id,
            "new_model_version_id": new_id,
            "old_status": old["status"],
            "old_capability_preserved": old["attrs"]["capability"],
            "new_has_capability": "capability" in new["attrs"],
            "fingerprint_previous": "cn_baseline_observatory",
            "fingerprint_current": new["attrs"]["drift_fingerprint"],
            "sources": list(SOURCES),
        }
        (M2_DIR / "exit-evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
        )
        (M2_DIR / "catalog-sample.json").write_text(
            json.dumps(
                {
                    "schema": SCHEMA_ID,
                    "active_priced": list_active_priced_models(build_catalog_document())[:4],
                    "node_kinds": sorted({n["kind"] for n in build_catalog_document().nodes}),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def test_no_network_imports_in_ingest_sources():
    ingest_dir = REPO_ROOT / "src" / "compass" / "ingest"
    forbidden = ("requests", "httpx", "urllib.request", "aiohttp")
    for path in ingest_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not import/use {token}"
        assert "sk-" not in text
