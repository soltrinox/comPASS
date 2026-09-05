"""Paired compressor CC-8 bundle helpers (Tier 4 / M4).

Canonical export/import live in chat-compressor CC-8. This module documents
the pairing and optionally delegates when the peer package is installed.
"""

from __future__ import annotations

from typing import Any


def export_bundle(_graph_root: str, **_kwargs: Any) -> Any:
    try:
        from chat_compressor.bundle import export_bundle as _export
    except ImportError as exc:  # pragma: no cover
        raise NotImplementedError(
            "Bundle export requires chat-compressor CC-8"
        ) from exc
    return _export(_graph_root, **_kwargs)


def import_bundle(_bundle_root: str, **_kwargs: Any) -> Any:
    try:
        from chat_compressor.bundle import import_bundle as _import
    except ImportError as exc:  # pragma: no cover
        raise NotImplementedError(
            "Bundle import requires chat-compressor CC-8"
        ) from exc
    return _import(_bundle_root, **_kwargs)
