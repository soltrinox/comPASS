#!/usr/bin/env python3
"""Fail-open / decide parity: Python compass.core vs Wasmer WASM CLI.

Writes evidence under test-results/wasmer-parity/.
Exit 0 on match; non-zero on divergence (release blocker).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "wasmer" / "fixtures" / "snapshot_min.json"
WASM = ROOT / "wasmer" / "artifacts" / "compass-decide.wasm"
OUT_DIR = ROOT / "test-results" / "wasmer-parity"
NOW = "2026-09-05T00:00:00Z"
REQUEST = "implement a function"

COMPARE_KEYS = (
    "selected_model_version_id",
    "task_class_id",
    "fail_open",
    "default_reason",
    "rationale",
    "decided_at",
)


def python_decide(request: str, snapshot, *, now: str = NOW):
    from compass.core import decide_from_snapshot

    return decide_from_snapshot(request, snapshot, now_iso=now).to_json_dict()


def wasmer_decide(*, request: str, snapshot_path: Path | None = None, demo: str | None = None) -> dict:
    wasmer = shutil.which("wasmer")
    if not wasmer:
        raise RuntimeError("wasmer binary not found on PATH")
    if not WASM.is_file():
        raise RuntimeError(f"missing wasm artifact: {WASM}")
    cmd = [wasmer, "run", str(WASM)]
    if snapshot_path is not None:
        # Map wasmer/ so guest path /wasmer/fixtures/... works
        cmd += ["--volume", f"{ROOT / 'wasmer'}:/wasmer"]
        guest = f"/wasmer/fixtures/{snapshot_path.name}"
        cmd += ["--", "--request", request, "--snapshot", guest, "--now", NOW]
    elif demo:
        cmd += ["--", "--request", request, "--fail-open-demo", demo, "--now", NOW]
    else:
        raise ValueError("need snapshot_path or demo")
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    line = proc.stdout.strip().splitlines()[-1]
    return json.loads(line)


def score_close(a, b, tol=1e-9) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def compare(name: str, py: dict, wasm: dict) -> list[str]:
    errs = []
    for k in COMPARE_KEYS:
        if py.get(k) != wasm.get(k):
            errs.append(f"{name}: {k}: python={py.get(k)!r} wasm={wasm.get(k)!r}")
    if not score_close(py.get("score"), wasm.get("score")):
        errs.append(f"{name}: score: python={py.get('score')!r} wasm={wasm.get('score')!r}")
    # scores map (ids)
    py_scores = py.get("scores") or {}
    wasm_scores = wasm.get("scores") or {}
    if set(py_scores) != set(wasm_scores):
        errs.append(f"{name}: score keys diverge: {set(py_scores)} vs {set(wasm_scores)}")
    else:
        for mid in py_scores:
            if not score_close(py_scores[mid], wasm_scores[mid]):
                errs.append(f"{name}: scores[{mid}]: {py_scores[mid]!r} vs {wasm_scores[mid]!r}")
    return errs


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = []
    errors: list[str] = []

    # Valid fixture
    raw = FIXTURE.read_bytes()
    py = python_decide(REQUEST, raw)
    wasm = wasmer_decide(request=REQUEST, snapshot_path=FIXTURE)
    cases.append({"name": "fixture_min", "python": py, "wasm": wasm})
    errors.extend(compare("fixture_min", py, wasm))

    # Fail-open table
    for demo, snap in [
        ("missing", None),
        ("corrupt", b"{truncated"),
        ("empty", {"schema": "model-graph/v1", "nodes": [], "edges": []}),
    ]:
        req = "implement a function" if demo == "empty" else "x"
        py = python_decide(req, snap)
        wasm = wasmer_decide(request=req, demo=demo)
        cases.append({"name": demo, "python": py, "wasm": wasm})
        errors.extend(compare(demo, py, wasm))

    evidence = {
        "artifact": str(WASM.relative_to(ROOT)),
        "wasmer": subprocess.check_output(["wasmer", "--version"], text=True).strip(),
        "cases": cases,
        "errors": errors,
        "ok": not errors,
    }
    out = OUT_DIR / "parity.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"ok": evidence["ok"], "errors": errors, "evidence": str(out)}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    # Ensure src on path when not installed editable
    sys.path.insert(0, str(ROOT / "src"))
    raise SystemExit(main())
