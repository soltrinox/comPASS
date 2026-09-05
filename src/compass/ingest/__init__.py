"""Catalog ingest (Hugging Face, OpenRouter, Cursor) — Tier 1 Observatory.

Offline/mocked by default: adapters load fixtures under fixtures/observatory/.
Live HTTP is env-gated (COMPASS_PROBE_ALLOW_NETWORK) behind host allowlist;
credentials via compass.probe.credentials only. When live is denied, adapters
fail-open to the last-known fixture snapshot for Route consumers.
"""

from compass.ingest.catalog import (
    SOURCES,
    build_catalog_document,
    ingest_fixtures_into_store,
    list_active_priced_models,
)
from compass.ingest import cursor, huggingface, openrouter

__all__ = [
    "SOURCES",
    "build_catalog_document",
    "cursor",
    "huggingface",
    "ingest_fixtures_into_store",
    "list_active_priced_models",
    "openrouter",
]
