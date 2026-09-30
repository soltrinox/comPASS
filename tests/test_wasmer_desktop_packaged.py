"""Desktop B3: packaged .webc vs loose-artifact decide envelopes.

scripts/wasmer_parity.py remains the Python-vs-raw-wasm guard and still shells
`wasmer run` on wasmer/artifacts/compass-decide.wasm. This module only checks
that run-decide.sh's webc hop and wasm hop agree.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WASM = ROOT / "wasmer" / "artifacts" / "compass-decide.wasm"
SCRIPT = ROOT / "scripts" / "wasmer_desktop_packaged.py"
SHELL = ROOT / "wasmer" / "desktop" / "run-decide.sh"


@pytest.mark.skipif(shutil.which("wasmer") is None, reason="wasmer CLI not installed")
@pytest.mark.skipif(not WASM.is_file(), reason="compass-decide.wasm not built")
def test_desktop_packaged_webc_matches_loose_wasm():
    py = ROOT / ".venv" / "bin" / "python"
    exe = str(py) if py.is_file() else sys.executable
    proc = subprocess.run([exe, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    evidence = ROOT / "test-results" / "s-desktop-mobile" / "desktop-evidence.json"
    assert evidence.is_file()


def test_run_decide_shell_is_executable():
    assert SHELL.is_file()
    assert os.access(SHELL, os.X_OK)
    text = SHELL.read_text(encoding="utf-8")
    assert "wasmer package build" in text
    assert "PUBLISH-NOT_RUN" in text
    assert "wasmer/artifacts/compass-decide.wasm" in text
