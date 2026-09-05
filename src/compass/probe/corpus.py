"""Probe corpus loader — synthetic fixtures (offline).

Production intent (prototype §12.1): draw tasks from the user's context-graph
history (Fact/OpenItem/Event episodes). This skeleton loads **repo fixtures**
only — synthetic, contamination-safe, no user secrets.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CORPUS_ENV = "COMPASS_PROBE_CORPUS"
_KIND_HINTS = frozenset({"decision", "design", "outcome"})


def _repo_root() -> Path:
    # src/compass/probe/corpus.py -> parents[3] == repo root
    return Path(__file__).resolve().parents[3]


def default_corpus_path() -> Path:
    """Resolve the default synthetic corpus path (no machine-specific abs paths)."""
    override = os.environ.get(CORPUS_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return _repo_root() / "fixtures" / "probe" / "corpus.json"


def load_corpus(path: Path | str | None = None) -> dict[str, Any]:
    """Load and lightly validate a probe corpus JSON document."""
    p = Path(path) if path is not None else default_corpus_path()
    if not p.is_file():
        raise FileNotFoundError(f"probe corpus not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("probe corpus root must be an object")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("probe corpus must include a tasks list")
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{i}] must be an object")
        for key in ("id", "prompt", "task_class"):
            if key not in task:
                raise ValueError(f"tasks[{i}] missing required field {key!r}")
        hint = task.get("kind_hint")
        if hint is not None and hint not in _KIND_HINTS:
            raise ValueError(
                f"tasks[{i}] kind_hint must be one of {sorted(_KIND_HINTS)}, got {hint!r}"
            )
    return data


def sample_tasks(limit: int = 10, *, path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return up to ``limit`` synthetic fixture tasks (never user secrets)."""
    if limit < 0:
        raise ValueError("limit must be >= 0")
    data = load_corpus(path)
    tasks = list(data.get("tasks") or [])
    return tasks[:limit]
