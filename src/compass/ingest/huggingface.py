"""Hugging Face Hub catalog ingest — offline fixtures only (Tier 1 Observatory).

No network. No provider API keys. Loads fixtures/observatory/huggingface.json.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from compass.ingest.catalog import (
    entries_from_fixture,
    fixture_path,
    load_fixture,
)


def fetch_catalog(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return normalized HF catalog entries from the offline fixture.

    Never performs HTTP. ``path`` may override the default fixture file.
    """
    data = load_fixture("huggingface", path=path)
    return entries_from_fixture(data)


def load_raw(path: Path | str | None = None) -> dict[str, Any]:
    """Load the raw HF fixture document."""
    return load_fixture("huggingface", path=path or fixture_path("huggingface"))
