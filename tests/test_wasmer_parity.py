"""WASM vs Python fail-open / decide parity (Track D)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WASM = ROOT / "wasmer" / "artifacts" / "compass-decide.wasm"
SCRIPT = ROOT / "scripts" / "wasmer_parity.py"


@pytest.mark.skipif(shutil.which("wasmer") is None, reason="wasmer CLI not installed")
@pytest.mark.skipif(not WASM.is_file(), reason="compass-decide.wasm not built")
def test_wasmer_python_parity_script():
    env = os.environ.copy()
    # Prefer project venv python if present
    py = ROOT / ".venv" / "bin" / "python"
    exe = str(py) if py.is_file() else sys.executable
    proc = subprocess.run([exe, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
