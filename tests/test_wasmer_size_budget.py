"""Track J: committed Wasmer artifacts honor SHA256SUMS + size budget."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "wasmer_size_budget.py"


def test_wasmer_size_budget_script():
    proc = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
    out = ROOT / "test-results" / "j-wasmer-packaging" / "size-budget.json"
    assert out.is_file()
