"""Credential boundary: Probe-only loaders; core/route/proxy never import them."""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
CRED_MOD = "compass.probe.credentials"

FORBIDDEN_IMPORT_ROOTS = (
    SRC / "compass" / "core",
    SRC / "compass" / "route",
    SRC / "compass" / "serve",
)
WASMER_ROOT = REPO / "wasmer"

PROVIDER_ENV_NAMES = frozenset(
    {
        "OPENROUTER_API_KEY",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "CURSOR_API_KEY",
    }
)


def _collect_imports(py_path: Path) -> set[str]:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _iter_py(root: Path):
    if not root.exists():
        return
    for path in root.rglob("*.py"):
        yield path


def test_env_example_has_placeholders_only():
    text = (REPO / ".env.example").read_text(encoding="utf-8")
    for name in ("OPENROUTER_API_KEY", "HF_TOKEN", "CURSOR_API_KEY"):
        assert name in text
    for line in text.splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in PROVIDER_ENV_NAMES or key.endswith("_API_KEY") or key == "HF_TOKEN":
            assert val in {"", "0", "1", "false", "true"}, (
                f".env.example must not hold real secrets: {key}={val!r}"
            )


def test_core_route_serve_sources_do_not_import_credentials():
    offenders: list[str] = []
    for root in FORBIDDEN_IMPORT_ROOTS:
        for path in _iter_py(root):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == CRED_MOD or alias.name.startswith(CRED_MOD + "."):
                            offenders.append(f"{path.relative_to(REPO)} -> {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod == CRED_MOD or mod.startswith(CRED_MOD + "."):
                        offenders.append(f"{path.relative_to(REPO)} -> from {mod}")
                    if mod == "compass.probe":
                        for alias in node.names:
                            if alias.name == "credentials":
                                offenders.append(
                                    f"{path.relative_to(REPO)} -> from compass.probe import credentials"
                                )
    assert offenders == [], f"forbidden credential imports: {offenders}"


def test_wasmer_tree_has_no_credential_module_refs():
    offenders: list[str] = []
    for path in WASMER_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".js", ".ts", ".rs", ".toml", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "compass.probe.credentials" in text or "load_openrouter_api_key" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == [], f"wasmer references Probe credentials: {offenders}"


def test_importing_core_does_not_load_credentials_module():
    for name in list(sys.modules):
        if name == CRED_MOD or name.startswith("compass.probe"):
            del sys.modules[name]
    importlib.import_module("compass.core")
    importlib.import_module("compass.core.decide")
    assert CRED_MOD not in sys.modules


def test_importing_route_does_not_load_credentials_module():
    for name in list(sys.modules):
        if name == CRED_MOD or name.startswith("compass.probe"):
            del sys.modules[name]
    importlib.import_module("compass.route")
    importlib.import_module("compass.route.decide")
    assert CRED_MOD not in sys.modules


def test_importing_serve_proxy_does_not_load_credentials_module():
    for name in list(sys.modules):
        if name == CRED_MOD or name.startswith("compass.probe"):
            del sys.modules[name]
    importlib.import_module("compass.serve.proxy")
    assert CRED_MOD not in sys.modules


def test_loaders_resolve_from_env(monkeypatch):
    from compass.probe import credentials as cred

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-placeholder")
    monkeypatch.setenv("HF_TOKEN", "hf_test_placeholder")
    monkeypatch.setenv("CURSOR_API_KEY", "cursor_test_placeholder")
    monkeypatch.setattr(cred, "_keychain_get", lambda account: None)
    assert cred.load_openrouter_api_key() == "sk-or-test-placeholder"
    assert cred.load_huggingface_token() == "hf_test_placeholder"
    assert cred.load_cursor_api_key() == "cursor_test_placeholder"


def test_loaders_return_none_when_unset(monkeypatch):
    from compass.probe import credentials as cred

    for k in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(cred, "_keychain_get", lambda account: None)
    assert cred.load_openrouter_api_key() is None
    assert cred.load_huggingface_token() is None
    assert cred.load_cursor_api_key() is None


def test_forbidden_caller_refuses(monkeypatch):
    """Simulate compass.route caller frame → CredentialBoundaryError."""
    from compass.probe import credentials as cred

    monkeypatch.setenv("OPENROUTER_API_KEY", "should-not-leak")
    ns = {"__name__": "compass.route.decide", "cred": cred}
    exec("def _go():\n    return cred.load_openrouter_api_key()\n", ns)
    with pytest.raises(cred.CredentialBoundaryError, match="forbidden caller"):
        ns["_go"]()


def test_audit_presence_redacted(monkeypatch):
    from compass.probe import credentials as cred

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret-do-not-log")
    monkeypatch.setattr(cred, "_keychain_get", lambda account: None)
    rows = cred.audit_credential_presence()
    blob = repr(rows)
    assert "sk-secret-do-not-log" not in blob
    assert all(r.get("value_redacted") is True for r in rows)
    or_row = next(r for r in rows if r["provider"] == "openrouter")
    assert or_row["present_in_env"] is True


def test_core_route_sources_do_not_reference_provider_env_names():
    offenders: list[str] = []
    roots = [SRC / "compass" / "core", SRC / "compass" / "route"]
    for root in roots:
        for path in _iter_py(root):
            text = path.read_text(encoding="utf-8")
            for name in PROVIDER_ENV_NAMES:
                if name in text:
                    offenders.append(f"{path.relative_to(REPO)} mentions {name}")
    assert offenders == [], offenders


def test_docs_probe_credentials_exist():
    assert (REPO / "docs" / "probe" / "CREDENTIALS.md").is_file()
    assert (REPO / "docs" / "probe" / "ROTATION.md").is_file()
    cred = (REPO / "docs" / "probe" / "CREDENTIALS.md").read_text(encoding="utf-8")
    for needle in ("OpenRouter", "Hugging Face", "Cursor", "COMPASS_PROXY"):
        assert needle in cred
