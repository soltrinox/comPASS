"""OpenRouter catalog ingest — offline fixtures only (Tier 1 Observatory).

No network. No provider API keys. Loads fixtures/observatory/openrouter.json.
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
    """Return normalized OpenRouter catalog entries from the offline fixture."""
    data = load_fixture("openrouter", path=path)
    return entries_from_fixture(data)


def load_raw(path: Path | str | None = None) -> dict[str, Any]:
    """Load the raw OpenRouter fixture document."""
    return load_fixture("openrouter", path=path or fixture_path("openrouter"))
