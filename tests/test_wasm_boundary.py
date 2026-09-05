"""WASM boundary: core must not import probe/ingest/serve or key modules."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

FORBIDDEN_PREFIXES = (
    "compass.probe",
    "compass.ingest",
    "compass.serve",
    "compass.native.keys",
)

CORE_ROOT = Path(__file__).resolve().parents[1] / "src" / "compass" / "core"


def _collect_imports_from_core_sources() -> set[str]:
    found: set[str] = set()
    for path in CORE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    found.add(node.module)
    return found


def test_core_sources_do_not_import_native_sidecar():
    imports = _collect_imports_from_core_sources()
    offenders = sorted(
        mod
        for mod in imports
        if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_PREFIXES)
    )
    assert offenders == [], f"core sources import forbidden modules: {offenders}"


def test_importing_compass_core_does_not_load_probe_ingest_serve():
    """Import core in a subprocess-like clean check via importlib without sys purge.

    Uses source AST for static denial; this test checks runtime module table
    after importing core alone when forbidden packages are not already loaded.
    """
    # Drop forbidden packages if somehow loaded so we can see fresh pulls.
    for name in list(sys.modules):
        if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
            del sys.modules[name]

    importlib.import_module("compass.core")
    importlib.import_module("compass.core.decide")
    importlib.import_module("compass.core.abi")
    loaded = [n for n in sys.modules if n.startswith("compass.")]
    for prefix in FORBIDDEN_PREFIXES:
        assert not any(n == prefix or n.startswith(prefix + ".") for n in loaded), (
            f"forbidden module loaded after compass.core import: {prefix}; loaded={loaded}"
        )


def test_host_abi_forbids_keys_namespace():
    from compass.core.abi import FORBIDDEN_HOST_NAMESPACES, COMPASS_HOST_ABI

    assert "keys" in FORBIDDEN_HOST_NAMESPACES
    assert COMPASS_HOST_ABI.startswith("1.")


def test_assert_no_key_material_rejects_api_key():
    from compass.core.abi import assert_no_key_material

    with pytest.raises(ValueError, match="forbidden key material"):
        assert_no_key_material({"OPENROUTER_API_KEY": "sk-test"})


def test_assert_no_key_material_allows_clean_snapshot():
    from compass.core.abi import assert_no_key_material

    assert_no_key_material(b'{"schema":"model-graph/v1","nodes":[],"edges":[]}')


def test_abi_json_browser_omits_fetch():
    import json

    abi_path = Path(__file__).resolve().parents[1] / "docs" / "abi" / "host-abi.v1.json"
    data = json.loads(abi_path.read_text(encoding="utf-8"))
    assert "keys" in data["forbidden_namespaces"]
    fetch = next(i for i in data["imports"] if i["namespace"] == "fetch")
    assert fetch["browser"] is False
    assert fetch.get("optional") is True
