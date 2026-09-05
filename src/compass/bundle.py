"""Paired compressor CC-8 bundle helpers (Tier 4 / M4) + local free fallback.

Canonical export/import live in chat-compressor CC-8 when installed.
Otherwise ``compass.sync.local_bundle`` provides a free manual portable
graph+meta bundle (test-ready; not full CC-8 tensor fidelity).

Automated cross-machine sync is **paid** — see ``compass.sync.automation``.
"""

from __future__ import annotations

from typing import Any


def export_bundle(_graph_root: str, **_kwargs: Any) -> Any:
    """Manual export (free). Prefers chat-compressor CC-8; else local bundle."""
    try:
        from chat_compressor.bundle import export_bundle as _export
    except ImportError:
        from compass.sync.local_bundle import export_local_bundle

        dest = _kwargs.get("dest") or _kwargs.get("bundle_root")
        if dest is None:
            raise TypeError(
                "local bundle export requires dest= (chat-compressor not installed)"
            )
        return export_local_bundle(
            _graph_root,
            dest,
            agent_id=_kwargs.get("agent_id"),
            extra_manifest=_kwargs.get("extra_manifest"),
        )
    return _export(_graph_root, **_kwargs)


def import_bundle(_bundle_root: str, **_kwargs: Any) -> Any:
    """Manual import (free). Prefers chat-compressor CC-8; else local bundle."""
    try:
        from chat_compressor.bundle import import_bundle as _import
    except ImportError:
        from compass.sync.local_bundle import import_local_bundle

        dest = _kwargs.get("dest") or _kwargs.get("graph_root") or _kwargs.get("dest_graph_root")
        if dest is None:
            raise TypeError(
                "local bundle import requires dest= (chat-compressor not installed)"
            )
        return import_local_bundle(
            _bundle_root,
            dest,
            verify=_kwargs.get("verify", True),
        )
    return _import(_bundle_root, **_kwargs)
