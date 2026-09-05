"""Catalog ingest (Hugging Face, OpenRouter, Cursor) — Tier 1 Observatory.

Offline/mocked: adapters load fixtures under fixtures/observatory/. No network.
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
