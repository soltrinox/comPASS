"""WASM-safe classify — re-exports pure keyword classifier (no network, no keys)."""

from __future__ import annotations

from compass.route.classify import DEFAULT_TASK_CLASS, classify, keyword_set

__all__ = ["DEFAULT_TASK_CLASS", "classify", "keyword_set"]
