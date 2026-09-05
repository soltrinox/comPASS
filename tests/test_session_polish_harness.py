"""Track H: invoke session_polish_harness against local comPREssOR when present."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "session_polish_harness.py"
DEFAULT_COMPRESSOR = ROOT.parent / "comPREssOR"


def _compressor_available() -> bool:
    root = Path(os.environ.get("COMPRESSOR_ROOT", str(DEFAULT_COMPRESSOR))).expanduser()
    return (root / "engine" / "src" / "chat_compressor" / "hook_cli.py").is_file()


def _harness_python() -> str:
    for cand in (
        DEFAULT_COMPRESSOR / "engine" / ".venv" / "bin" / "python",
        DEFAULT_COMPRESSOR / "engine" / ".venv" / "bin" / "python3",
    ):
        if cand.is_file():
            return str(cand)
    return sys.executable


@pytest.mark.skipif(not _compressor_available(), reason="comPREssOR checkout not adjacent")
def test_session_polish_harness_green():
    env = os.environ.copy()
    env.setdefault("COMPRESSOR_ROOT", str(DEFAULT_COMPRESSOR.resolve()))
    pp = [
        str(ROOT / "src"),
        str(DEFAULT_COMPRESSOR / "engine" / "src"),
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = os.pathsep.join(x for x in pp if x)
    proc = subprocess.run(
        [_harness_python(), str(HARNESS)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    evidence = ROOT / "test-results" / "h-session-polish" / "evidence.json"
    assert evidence.is_file()
    data = evidence.read_text(encoding="utf-8")
    assert '"pass": true' in data or '"pass": true\n' in data or '"pass": true,' in data
