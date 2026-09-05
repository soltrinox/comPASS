"""Map a request to a TaskClass before any answer is known.

C2: light keyword features only — does not import chat-compressor or Probe.
Concepts mirror extractive.keyword_set / capability axes from docs.
Classification never calls the network.
"""

from __future__ import annotations

import re
from typing import Any

# Seed clusters aligned with prototype capability axes / common task classes.
_TASK_KEYWORDS: dict[str, frozenset[str]] = {
    "code_generation": frozenset(
        {"code", "implement", "function", "class", "refactor", "bug", "fix", "compile", "test"}
    ),
    "multi_step_plan": frozenset(
        {"plan", "roadmap", "milestone", "orchestrat", "multi-step", "architecture"}
    ),
    "structured_output": frozenset(
        {"json", "schema", "yaml", "structured", "table", "csv"}
    ),
    "long_context": frozenset(
        {"summarize", "transcript", "long", "document", "corpus", "context"}
    ),
    "agentic_tool_use": frozenset(
        {"tool", "browser", "shell", "api", "call", "agent"}
    ),
}

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_./#-]*", re.I)

DEFAULT_TASK_CLASS = "general"


def keyword_set(text: str, *, limit: int = 64) -> set[str]:
    """Lightweight keyword extraction (compressor-concept stub, no import)."""
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(text or ""):
        tok = match.group(0).lower()
        if len(tok) < 2:
            continue
        tokens.append(tok)
        if len(tokens) >= limit * 4:
            break
    # Prefer longer / rarer-looking tokens
    uniq = sorted(set(tokens), key=lambda t: (-len(t), t))
    return set(uniq[:limit])


def classify(request: str, graph_snapshot: dict[str, Any] | None = None) -> str:
    """Classify prompt (+ optional graph snapshot) → TaskClass id string.

    Biases toward over-provisioning on hard/uncertain classes when scores tie.
    """
    _ = graph_snapshot  # reserved: future use of TaskClass nodes from graph
    kws = keyword_set(request)
    if not kws:
        return DEFAULT_TASK_CLASS

    best_class = DEFAULT_TASK_CLASS
    best_score = 0
    # Prefer harder classes on ties (over-provision): listed later wins on equal score
    order = [
        "general",
        "structured_output",
        "long_context",
        "code_generation",
        "agentic_tool_use",
        "multi_step_plan",
    ]
    for task_class in order:
        seeds = _TASK_KEYWORDS.get(task_class, frozenset())
        score = sum(1 for k in kws if any(k.startswith(s) or s in k for s in seeds))
        if score >= best_score:
            best_score = score
            best_class = task_class if score > 0 else DEFAULT_TASK_CLASS
    return best_class if best_score > 0 else DEFAULT_TASK_CLASS
