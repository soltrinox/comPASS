#!/usr/bin/env python3
"""CI guard: SHA256SUMS match + browser cdylib size budget (Track J)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "wasmer" / "artifacts"
SUMS = ART / "SHA256SUMS"
OUT = ROOT / "test-results" / "j-wasmer-packaging" / "size-budget.json"

# Soft ceiling for browser cdylib (~101 KiB today). Fail if regresses past this.
BROWSER_BUDGET_BYTES = 150_000
BROWSER_NAME = "compass_core_bg.wasm"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_sums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        name = Path(name).name
        out[name] = digest
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    if not SUMS.is_file():
        errors.append(f"missing {SUMS}")
        evidence = {"ok": False, "errors": errors}
        OUT.write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))
        return 1

    expected = parse_sums(SUMS.read_text(encoding="utf-8"))
    sizes: dict[str, int] = {}
    actual: dict[str, str] = {}
    for name, digest in sorted(expected.items()):
        path = ART / name
        if not path.is_file():
            errors.append(f"missing artifact: {name}")
            continue
        got = sha256(path)
        actual[name] = got
        sizes[name] = path.stat().st_size
        if got != digest:
            errors.append(f"SHA256 mismatch {name}: expected {digest} got {got}")

    browser_size = sizes.get(BROWSER_NAME)
    if browser_size is None:
        errors.append(f"missing size for {BROWSER_NAME}")
    elif browser_size > BROWSER_BUDGET_BYTES:
        errors.append(
            f"size budget exceeded for {BROWSER_NAME}: {browser_size} > {BROWSER_BUDGET_BYTES}"
        )

    evidence = {
        "ok": not errors,
        "budget_bytes": BROWSER_BUDGET_BYTES,
        "sizes": sizes,
        "sha256_expected": expected,
        "sha256_actual": actual,
        "errors": errors,
    }
    OUT.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
