"""Track L: version lockstep + release docs present; no secrets in packaging files."""

from __future__ import annotations

import tomllib
from pathlib import Path

import compass
from compass.core import CORE_MODULE_VERSION

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_version_lockstep():
    proj = _pyproject()["project"]
    assert proj["name"] == "compass-router"
    assert proj["version"] == compass.__version__ == CORE_MODULE_VERSION == "0.1.0"


def test_release_docs_exist():
    for rel in (
        "LICENSE",
        "CHANGELOG.md",
        "docs/RELEASE.md",
        ".github/workflows/release.yml",
        "MANIFEST.in",
    ):
        assert (ROOT / rel).is_file(), rel


def test_changelog_has_phase1_section():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.1.0]" in text
    assert "Phase 1" in text
    assert "[Unreleased]" in text


def test_release_workflow_is_opt_in():
    yml = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in yml
    assert "publish_target" in yml
    assert "TWINE_PASSWORD" in yml
    # must not run on every push to main
    assert "branches: [main]" not in yml


def test_packaging_files_have_no_live_tokens():
    """Refuse accidental live token paste into committed release docs."""
    import re

    # Real PyPI API tokens are long base64-ish after the pypi- prefix.
    live_token = re.compile(r"pypi-[A-Za-z0-9_-]{20,}")
    for rel in (
        "CHANGELOG.md",
        "docs/RELEASE.md",
        ".github/workflows/release.yml",
        "pyproject.toml",
        "LICENSE",
    ):
        body = (ROOT / rel).read_text(encoding="utf-8")
        for m in live_token.finditer(body):
            assert m.group(0).endswith("...") or set(m.group(0)[5:]) <= {".", "-", "_"}, (
                f"{rel} looks like a live token near {m.group(0)[:12]!r}"
            )
