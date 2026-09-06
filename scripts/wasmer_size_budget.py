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
# ENI6MA Path-B wasm is intentionally larger and is digest-checked only (not size-budgeted).
BROWSER_BUDGET_BYTES = 150_000
BROWSER_NAME = "compass_core_bg.wasm"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_sums(text: str) -> dict[str, str]:
    """Map logical artifact key -> digest.

    Keys are basenames for flat compass artifacts, or repo-relative paths under
    wasmer/artifacts/ when the SUMS line includes a nested path (e.g. eni6ma/...).
    """
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        key = _sum_key(name)
        out[key] = digest
    return out


def _sum_key(name_field: str) -> str:
    raw = Path(name_field)
    parts = list(raw.parts)
    # Normalize legacy "../artifacts/..." entries written relative to wasmer/.
    while parts and parts[0] == "..":
        parts = parts[1:]
    if parts and parts[0] == "artifacts":
        parts = parts[1:]
    if not parts:
        return raw.name
    # Flat file in ART root → basename key (backward compatible).
    if len(parts) == 1:
        return parts[0]
    return "/".join(parts)


def resolve_artifact(key: str) -> Path | None:
    """Resolve a SUMS key to a file under wasmer/artifacts/."""
    direct = ART / key
    if direct.is_file():
        return direct
    # Basename fallback + unique rglob (nested Path-B layouts).
    base = Path(key).name
    flat = ART / base
    if flat.is_file():
        return flat
    matches = [p for p in ART.rglob(base) if p.is_file()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer path that ends with the key when key is nested.
        for m in matches:
            try:
                if m.relative_to(ART).as_posix() == key:
                    return m
            except ValueError:
                pass
    return None


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
    for key, digest in sorted(expected.items()):
        path = resolve_artifact(key)
        if path is None:
            errors.append(f"missing artifact: {key}")
            continue
        got = sha256(path)
        # Report under basename for flat keys; nested keys keep relative path.
        report_name = Path(key).name if "/" not in key else key
        actual[report_name] = got
        sizes[report_name] = path.stat().st_size
        if got != digest:
            errors.append(f"SHA256 mismatch {key}: expected {digest} got {got}")

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
