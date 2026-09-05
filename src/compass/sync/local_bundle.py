"""comPASS-local portable bundle (CC-8-shaped) for free manual export/import.

Layout (bundle/v1 concepts without requiring chat-compressor):
  manifest.json   — schema, version, producer, checksums, lineage head
  graph.json      — model-graph document (capability graph slice)
  bandit-posterior.json — optional bandit state
  inject_ledger.json — optional empty ledger stub (pairing hook)
  lineage.json    — optional lineage stub

This is **not** a claim of identical CC-8 tensor/state fidelity — only a
test-ready portable graph+meta bundle for sync automation spikes.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BUNDLE_SCHEMA = "bundle/v1"
BUNDLE_PRODUCER = "compass-router/local-bundle"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def export_local_bundle(
    graph_root: str | Path,
    dest: str | Path,
    *,
    agent_id: str | None = None,
    extra_manifest: dict[str, Any] | None = None,
) -> Path:
    """Export a GraphStore root (or bare graph dir) into a portable bundle dir.

    Free-tier surface — no paid feature flag required.
    """
    root = Path(graph_root)
    out = Path(dest)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    graph_src = root / "graph" / "model-graph.json"
    if not graph_src.exists():
        # Accept a root that *is* the graph file or a document path.
        if root.is_file() and root.name.endswith(".json"):
            graph_src = root
        elif (root / "model-graph.json").exists():
            graph_src = root / "model-graph.json"
        else:
            # Create minimal empty graph so round-trip still works.
            graph_src = None

    if graph_src is not None:
        graph_data = _read_json(graph_src)
    else:
        graph_data = {"schema": "model-graph/v1", "nodes": [], "edges": []}

    graph_path = out / "graph.json"
    _write_json(graph_path, graph_data)

    bandit_src = root / "graph" / "bandit-posterior.json"
    if not bandit_src.exists():
        bandit_src = root / "bandit-posterior.json"
    bandit_checksum = None
    if bandit_src.exists():
        shutil.copy2(bandit_src, out / "bandit-posterior.json")
        bandit_checksum = _sha256_file(out / "bandit-posterior.json")

    _write_json(
        out / "inject_ledger.json",
        {"schema": "inject-ledger/v1", "entries": [], "note": "stub — CC-2 pairing"},
    )
    _write_json(
        out / "lineage.json",
        {
            "schema": "lineage/v1",
            "head": agent_id or "local",
            "entries": [],
            "note": "stub — conflict = branch not LWW (PAID-PILLARS Pillar 1)",
        },
    )

    checksums = {
        "graph.json": _sha256_file(graph_path),
        "inject_ledger.json": _sha256_file(out / "inject_ledger.json"),
        "lineage.json": _sha256_file(out / "lineage.json"),
    }
    if bandit_checksum:
        checksums["bandit-posterior.json"] = bandit_checksum

    manifest: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "version": 1,
        "producer": BUNDLE_PRODUCER,
        "exported_at": _now_iso(),
        "agent_id": agent_id or "local",
        "checksums": checksums,
        "layout": {
            "manifest.json": "present",
            "graph.json": "model-graph/v1",
            "bandit-posterior.json": "optional",
            "inject_ledger.json": "stub",
            "lineage.json": "stub",
        },
        "equivalence_note": (
            "Outcome-equivalence bands only when measured; "
            "never identical cross-model text."
        ),
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    _write_json(out / "manifest.json", manifest)
    return out


def verify_bundle(bundle_root: str | Path) -> dict[str, Any]:
    """Verify manifest + checksums; raise ValueError on mismatch."""
    root = Path(bundle_root)
    man_path = root / "manifest.json"
    if not man_path.exists():
        raise ValueError(f"missing manifest.json under {root}")
    manifest = _read_json(man_path)
    if manifest.get("schema") != BUNDLE_SCHEMA:
        raise ValueError(f"unexpected bundle schema: {manifest.get('schema')!r}")
    checksums = manifest.get("checksums") or {}
    for name, expect in checksums.items():
        path = root / name
        if not path.exists():
            raise ValueError(f"missing bundle file {name}")
        got = _sha256_file(path)
        if got != expect:
            raise ValueError(f"checksum mismatch for {name}: {got} != {expect}")
    return manifest


def import_local_bundle(
    bundle_root: str | Path,
    dest_graph_root: str | Path,
    *,
    verify: bool = True,
) -> Path:
    """Import a portable bundle into a GraphStore-shaped root.

    Free-tier surface — no paid feature flag required.
    """
    src = Path(bundle_root)
    if verify:
        verify_bundle(src)
    dest = Path(dest_graph_root)
    graph_dir = dest / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)

    graph_src = src / "graph.json"
    if not graph_src.exists():
        raise ValueError("bundle missing graph.json")
    shutil.copy2(graph_src, graph_dir / "model-graph.json")

    bandit = src / "bandit-posterior.json"
    if bandit.exists():
        shutil.copy2(bandit, graph_dir / "bandit-posterior.json")

    # Keep a copy of sync metadata for lineage/audit.
    meta = dest / "bundle-import-meta"
    meta.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "inject_ledger.json", "lineage.json"):
        p = src / name
        if p.exists():
            shutil.copy2(p, meta / name)
    return dest


__all__ = [
    "BUNDLE_PRODUCER",
    "BUNDLE_SCHEMA",
    "export_local_bundle",
    "import_local_bundle",
    "verify_bundle",
]
