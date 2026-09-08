#!/usr/bin/env python3
"""Packaged .webc vs loose-artifact decide parity for desktop B3.

Does not replace scripts/wasmer_parity.py (Python vs raw wasm). This checks
that wasmer/desktop/run-decide.sh's local .webc hop and its air-gap wasm hop
emit the same decide envelope / reason codes.

Writes desktop-only evidence under test-results/s-desktop-mobile/.
Registry-by-name is recorded PARTIAL / NOT_RUN — never faked.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "wasmer" / "desktop" / "run-decide.sh"
WASM = ROOT / "wasmer" / "artifacts" / "compass-decide.wasm"
OUT_DIR = ROOT / "test-results" / "s-desktop-mobile"
NOW = "2026-09-05T00:00:00Z"
REQUEST = "implement a function"

COMPARE_KEYS = (
    "selected_model_version_id",
    "task_class_id",
    "fail_open",
    "default_reason",
    "rationale",
    "decided_at",
    "score",
    "scores",
    "module_version",
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def score_close(a, b, tol=1e-9) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def compare(name: str, packaged: dict, loose: dict) -> list[str]:
    errs: list[str] = []
    for k in COMPARE_KEYS:
        if k == "score":
            if not score_close(packaged.get(k), loose.get(k)):
                errs.append(f"{name}: score: packaged={packaged.get(k)!r} loose={loose.get(k)!r}")
            continue
        if k == "scores":
            a = packaged.get("scores") or {}
            b = loose.get("scores") or {}
            if set(a) != set(b):
                errs.append(f"{name}: score keys diverge: {set(a)} vs {set(b)}")
            else:
                for mid in a:
                    if not score_close(a[mid], b[mid]):
                        errs.append(f"{name}: scores[{mid}]: {a[mid]!r} vs {b[mid]!r}")
            continue
        if packaged.get(k) != loose.get(k):
            errs.append(f"{name}: {k}: packaged={packaged.get(k)!r} loose={loose.get(k)!r}")
    return errs


def run_decide(env_extra: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_extra)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def parse_envelope(stdout: str) -> dict:
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
    if not lines:
        raise ValueError("empty stdout; expected a decide envelope")
    return json.loads(lines[-1])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = _ts()
    errors: list[str] = []
    cases: list[dict] = []

    if shutil.which("wasmer") is None:
        print(json.dumps({"ok": False, "errors": ["wasmer binary not found on PATH"]}, indent=2))
        return 1
    if not SCRIPT.is_file() or not os.access(SCRIPT, os.X_OK):
        print(json.dumps({"ok": False, "errors": [f"missing executable {_rel(SCRIPT)}"]}, indent=2))
        return 1
    if not WASM.is_file():
        print(json.dumps({"ok": False, "errors": [f"missing {_rel(WASM)}"]}, indent=2))
        return 1

    wasmer_ver = subprocess.check_output(["wasmer", "--version"], text=True).strip()

    # --- packaged webc vs loose wasm (fixture + one fail-open reason code) ---
    scenarios = [
        {"name": "fixture_min", "env": {}},
        {"name": "fail_open_missing", "env": {"COMPASS_FAIL_OPEN_DEMO": "missing", "COMPASS_REQUEST": "x"}},
    ]
    for sc in scenarios:
        base = {
            "COMPASS_NOW": NOW,
            "COMPASS_REQUEST": sc["env"].get("COMPASS_REQUEST", REQUEST),
            **{k: v for k, v in sc["env"].items() if k != "COMPASS_REQUEST"},
        }
        webc = run_decide({**base, "COMPASS_DECIDE_SOURCE": "webc"})
        wasm = run_decide({**base, "COMPASS_DECIDE_SOURCE": "wasm"})
        case = {
            "name": sc["name"],
            "webc_rc": webc.returncode,
            "wasm_rc": wasm.returncode,
            "webc_stderr": webc.stderr.strip().splitlines()[-8:],
            "wasm_stderr": wasm.stderr.strip().splitlines()[-8:],
        }
        if webc.returncode != 0:
            errors.append(f"{sc['name']}: webc hop rc={webc.returncode}")
        if wasm.returncode != 0:
            errors.append(f"{sc['name']}: wasm hop rc={wasm.returncode}")
        packaged = loose = None
        if webc.returncode == 0:
            packaged = parse_envelope(webc.stdout)
            case["packaged"] = packaged
        if wasm.returncode == 0:
            loose = parse_envelope(wasm.stdout)
            case["loose"] = loose
        if packaged is not None and loose is not None:
            case["identical_parsed"] = packaged == loose
            errs = compare(sc["name"], packaged, loose)
            errors.extend(errs)
            case["compare_errors"] = errs
        cases.append(case)

    # --- registry-by-name: code present, runtime NOT_RUN ---
    reg_only = run_decide(
        {
            "COMPASS_WASMER_USE_REGISTRY": "1",
            "COMPASS_WASMER_REGISTRY_ONLY": "1",
            "COMPASS_NOW": NOW,
            "COMPASS_REQUEST": REQUEST,
        },
        "--registry",
    )
    registry = {
        "grade": "PARTIAL",
        "runtime": "NOT_RUN",
        "reason": (
            "Wasmer registry publish is NOT_RUN: no login, namespace compass unclaimed. "
            "run-decide.sh implements wasmer run <name>@<version> and falls through. "
            "This capture uses COMPASS_WASMER_REGISTRY_ONLY=1 so the hop cannot hide behind local .webc."
        ),
        "command": "COMPASS_WASMER_USE_REGISTRY=1 COMPASS_WASMER_REGISTRY_ONLY=1 ./wasmer/desktop/run-decide.sh --registry",
        "rc": reg_only.returncode,
        "stdout_empty": not reg_only.stdout.strip(),
        "stderr_tail": reg_only.stderr.strip().splitlines()[-16:],
        "publish_state_ref": "wasmer/PUBLISH-NOT_RUN.md",
        "faked": False,
    }
    if reg_only.returncode == 0:
        errors.append("registry-only hop unexpectedly succeeded; do not claim a published package")
        registry["grade"] = "UNEXPECTED_SUCCESS"
    else:
        blob = (reg_only.stderr or "") + (reg_only.stdout or "")
        honest = (
            "NOT_RUN" in blob
            or "not found" in blob.lower()
            or "Unable to find" in blob
            or "not on the registry" in blob
        )
        registry["honest_failure_logged"] = honest
        if not honest:
            errors.append("registry-only hop failed but did not log an honest NOT_RUN / not-found diagnostic")

    # Fall-through path: registry requested, then local webc must still emit an envelope.
    reg_fall = run_decide(
        {
            "COMPASS_WASMER_USE_REGISTRY": "1",
            "COMPASS_NOW": NOW,
            "COMPASS_REQUEST": REQUEST,
        }
    )
    fallthrough = {
        "rc": reg_fall.returncode,
        "stderr_mentions_fallthrough": "Falling through" in (reg_fall.stderr or ""),
        "stderr_mentions_webc": "source=webc" in (reg_fall.stderr or ""),
    }
    if reg_fall.returncode != 0:
        errors.append(f"registry-then-webc fallthrough rc={reg_fall.returncode}")
    else:
        env = parse_envelope(reg_fall.stdout)
        fallthrough["selected_model_version_id"] = env.get("selected_model_version_id")
        if env.get("selected_model_version_id") != "urn:mg:model:cheap":
            errors.append("fallthrough envelope did not select urn:mg:model:cheap")

    evidence = {
        "stage": "s-desktop-mobile",
        "plan_todo": "b3-desktop",
        "mobile_coverage": "none — desktop-only files; B4 owns mobile",
        "script": _rel(SCRIPT),
        "wasmer": wasmer_ver,
        "parity_script_untouched": "scripts/wasmer_parity.py still runs wasmer on the loose wasm artifact",
        "run_order": [
            "1 registry-by-name if requested (COMPASS_WASMER_USE_REGISTRY / --registry)",
            "2 local .webc (wasmer package build if missing) — default today",
            "3 air-gap wasmer/artifacts/compass-decide.wasm",
        ],
        "cases": cases,
        "registry_by_name": registry,
        "registry_fallthrough": fallthrough,
        "errors": errors,
        "ok": not errors,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    json_path = OUT_DIR / "desktop-evidence.json"
    json_path.write_text(json.dumps(evidence, indent=2) + "\n")

    # Timestamped transcripts: .log.txt is gitignored; sibling .txt is the committed copy.
    def write_pair(stem: str, body: str) -> None:
        (OUT_DIR / f"{stem}-{ts}.log.txt").write_text(body)
        (OUT_DIR / f"{stem}.txt").write_text(body)

    def fmt_case(c: dict) -> str:
        packed = json.dumps(c.get("packaged"), sort_keys=True)
        loose = json.dumps(c.get("loose"), sort_keys=True)
        ident = "IDENTICAL" if c.get("identical_parsed") else "DIVERGED"
        return (
            f"## {c['name']}\n"
            f"webc_rc={c['webc_rc']} wasm_rc={c['wasm_rc']} parsed={ident}\n"
            f"packaged: {packed}\n"
            f"loose:    {loose}\n"
        )

    write_pair(
        "desktop-packaged-vs-loose",
        "\n".join(
            [
                f"# packaged .webc vs loose wasm — captured {evidence['captured_at']}",
                f"# wasmer: {wasmer_ver}",
                f"# script: {_rel(SCRIPT)}",
                "",
                *[fmt_case(c) for c in cases],
                f"errors: {errors}",
                f"ok: {not errors}",
                "",
            ]
        ),
    )
    write_pair(
        "desktop-registry",
        "\n".join(
            [
                f"# registry-by-name — captured {evidence['captured_at']}",
                "# Grade: PARTIAL (code present). Runtime: NOT_RUN. Not faked.",
                f"rc={registry['rc']}",
                f"stdout_empty={registry['stdout_empty']}",
                "stderr:",
                *registry["stderr_tail"],
                "",
                f"fallthrough_rc={fallthrough['rc']}",
                f"fallthrough_logged={fallthrough.get('stderr_mentions_fallthrough')}",
                f"fallthrough_source_webc={fallthrough.get('stderr_mentions_webc')}",
                "",
            ]
        ),
    )

    print(
        json.dumps(
            {
                "ok": evidence["ok"],
                "errors": errors,
                "evidence": _rel(json_path),
                "registry_by_name": {"grade": "PARTIAL", "runtime": "NOT_RUN"},
            },
            indent=2,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
