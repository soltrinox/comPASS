#!/usr/bin/env python3
"""Regenerate the model-graph.v1.json mirrors from the canonical package copy.

Canonical source of truth:

    src/compass/schema/model-graph.v1.json

That path is canonical because ``compass.schema.loader`` reads it at runtime via
``importlib.resources``, and because ``[tool.setuptools.package-data]`` makes it the
only copy that ships in the sdist and wheel. The other two paths are mirrors kept for
machine consumers (``schema/``) and for docs readers (``docs/schema/``); neither is
packaged, so neither may be edited by hand.

Usage:

    python scripts/sync_schema.py            # rewrite both mirrors from canonical
    python scripts/sync_schema.py --check    # report drift, write nothing, exit 1 on drift

``tests/test_schema.py`` enforces the same digests, so drift fails the suite as well.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL = REPO_ROOT / "src" / "compass" / "schema" / "model-graph.v1.json"
MIRRORS = (
    REPO_ROOT / "schema" / "model-graph.v1.json",
    REPO_ROOT / "docs" / "schema" / "model-graph.v1.json",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify mirrors match canonical; write nothing; exit 1 on drift",
    )
    args = parser.parse_args(argv)

    if not CANONICAL.is_file():
        print(f"[FAIL] canonical schema missing: {rel(CANONICAL)}")
        return 2

    canonical_digest = sha256_file(CANONICAL)
    print(f"canonical {rel(CANONICAL)} sha256={canonical_digest}")

    drift = 0
    for mirror in MIRRORS:
        if not mirror.is_file():
            if args.check:
                print(f"[FAIL] mirror missing: {rel(mirror)}")
                drift += 1
                continue
            mirror.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(CANONICAL, mirror)
            print(f"[PASS] created {rel(mirror)}")
            continue

        mirror_digest = sha256_file(mirror)
        if mirror_digest == canonical_digest:
            print(f"[PASS] in sync {rel(mirror)}")
            continue

        if args.check:
            print(f"[FAIL] drift {rel(mirror)} sha256={mirror_digest}")
            drift += 1
        else:
            shutil.copyfile(CANONICAL, mirror)
            print(f"[PASS] rewrote {rel(mirror)} (was sha256={mirror_digest})")

    if drift:
        print(f"[FAIL] {drift} mirror(s) out of sync — run: python scripts/sync_schema.py")
        return 1

    print("[PASS] all model-graph.v1.json copies share one digest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
