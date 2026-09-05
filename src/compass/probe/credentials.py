"""Probe-only credential loaders (OpenRouter / Hugging Face / Cursor).

Normative boundary
------------------
* Provider API keys are resolved **only** for the Probe sidecar process.
* Callers whose stack includes ``compass.core``, ``compass.route``,
  ``compass.serve.proxy``, or Wasmer glue paths are refused.
* Route / Graph / hooks / browser WASM must never import this module.
* Tier-3 proxy may hold its **own** upstream service keys separately
  (``COMPASS_PROXY_*``); those are not Probe catalog credentials and must
  not be loaded through this module.

Storage
-------
Resolve order per provider: process environment, then optional OS keychain
(macOS Keychain via ``security``, or the optional ``keyring`` package).
Never read committed ``.env`` files from this module — operators export
vars or use a local untracked ``.env`` loaded by their shell/direnv.
"""

from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Final, Literal

Provider = Literal["openrouter", "huggingface", "cursor"]

# Canonical env var names (document in .env.example; placeholders only there).
ENV_OPENROUTER: Final = "OPENROUTER_API_KEY"
ENV_HUGGINGFACE: Final = "HF_TOKEN"
ENV_HUGGINGFACE_ALT: Final = "HUGGING_FACE_HUB_TOKEN"
ENV_CURSOR: Final = "CURSOR_API_KEY"

# Optional keychain service/account labels (never store real secrets in git).
KEYCHAIN_SERVICE: Final = "comPASS.probe"
KEYCHAIN_ACCOUNT: dict[Provider, str] = {
    "openrouter": "OPENROUTER_API_KEY",
    "huggingface": "HF_TOKEN",
    "cursor": "CURSOR_API_KEY",
}

# Modules / path fragments that must never resolve Probe credentials.
_FORBIDDEN_MODULE_PREFIXES: Final[tuple[str, ...]] = (
    "compass.core",
    "compass.route",
    "compass.serve.proxy",
    "compass.serve.advisory",
)
_FORBIDDEN_PATH_FRAGMENTS: Final[tuple[str, ...]] = (
    f"{os.sep}compass{os.sep}core{os.sep}",
    f"{os.sep}compass{os.sep}route{os.sep}",
    f"{os.sep}compass{os.sep}serve{os.sep}proxy",
    f"{os.sep}wasmer{os.sep}",
)


class CredentialBoundaryError(RuntimeError):
    """Raised when a credential load is attempted outside the Probe boundary."""


@dataclass(frozen=True)
class CredentialPresence:
    """Redacted presence report — never includes secret values."""

    provider: Provider
    env_var: str
    present_in_env: bool
    present_in_keychain: bool

    def to_audit_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "env_var": self.env_var,
            "present_in_env": self.present_in_env,
            "present_in_keychain": self.present_in_keychain,
            "value_redacted": True,
        }


def _frame_forbidden(module_name: str, filename: str) -> bool:
    if module_name:
        for prefix in _FORBIDDEN_MODULE_PREFIXES:
            if module_name == prefix or module_name.startswith(prefix + "."):
                return True
    if filename:
        normalized = filename.replace("/", os.sep).replace("\\", os.sep)
        for frag in _FORBIDDEN_PATH_FRAGMENTS:
            if frag in normalized:
                return True
    return False


def assert_probe_credential_boundary() -> None:
    """Refuse if any caller frame is Route / core / proxy / Wasmer glue."""
    for info in inspect.stack()[1:]:
        mod = info.frame.f_globals.get("__name__", "") or ""
        filename = (info.filename or "").replace("/", os.sep).replace("\\", os.sep)
        if mod.startswith("compass.probe"):
            continue
        under_tests = f"{os.sep}tests{os.sep}" in filename
        # Production forbidden module on the stack → refuse.
        # Test files may call loaders; only refuse when their globals claim a
        # forbidden production module name (simulated caller).
        if _frame_forbidden(mod, "" if under_tests else filename):
            raise CredentialBoundaryError(
                "refusing Probe credential load from forbidden caller "
                f"module={mod!r} file={filename!r}"
            )
        if under_tests or mod.startswith("tests.") or mod.startswith("test_"):
            continue


def _keychain_get(account: str) -> str | None:
    """Best-effort optional keychain read; never raises on missing tooling."""
    try:
        import keyring  # type: ignore

        value = keyring.get_password(KEYCHAIN_SERVICE, account)
        if value:
            return value.strip() or None
    except Exception:
        pass

    if sys.platform == "darwin" and shutil.which("security"):
        try:
            proc = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    KEYCHAIN_SERVICE,
                    "-a",
                    account,
                    "-w",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                secret = (proc.stdout or "").strip()
                return secret or None
        except Exception:
            pass
    return None


def _env_get(*names: str) -> str | None:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and raw.strip():
            return raw.strip()
    return None


def load_openrouter_api_key() -> str | None:
    """Return OpenRouter API key from env/keychain, or None if unset."""
    assert_probe_credential_boundary()
    return _env_get(ENV_OPENROUTER) or _keychain_get(KEYCHAIN_ACCOUNT["openrouter"])


def load_huggingface_token() -> str | None:
    """Return Hugging Face token (HF_TOKEN or HUGGING_FACE_HUB_TOKEN)."""
    assert_probe_credential_boundary()
    return (
        _env_get(ENV_HUGGINGFACE, ENV_HUGGINGFACE_ALT)
        or _keychain_get(KEYCHAIN_ACCOUNT["huggingface"])
    )


def load_cursor_api_key() -> str | None:
    """Return Cursor API key from env/keychain, or None if unset."""
    assert_probe_credential_boundary()
    return _env_get(ENV_CURSOR) or _keychain_get(KEYCHAIN_ACCOUNT["cursor"])


def load_provider_credential(provider: Provider) -> str | None:
    """Dispatch loader by provider id."""
    if provider == "openrouter":
        return load_openrouter_api_key()
    if provider == "huggingface":
        return load_huggingface_token()
    if provider == "cursor":
        return load_cursor_api_key()
    raise ValueError(f"unknown provider: {provider!r}")


def credential_presence(provider: Provider) -> CredentialPresence:
    """Redacted presence check (safe for audit logs)."""
    assert_probe_credential_boundary()
    if provider == "openrouter":
        env_var = ENV_OPENROUTER
        in_env = _env_get(ENV_OPENROUTER) is not None
    elif provider == "huggingface":
        env_var = ENV_HUGGINGFACE
        in_env = _env_get(ENV_HUGGINGFACE, ENV_HUGGINGFACE_ALT) is not None
    elif provider == "cursor":
        env_var = ENV_CURSOR
        in_env = _env_get(ENV_CURSOR) is not None
    else:
        raise ValueError(f"unknown provider: {provider!r}")
    in_kc = _keychain_get(KEYCHAIN_ACCOUNT[provider]) is not None
    return CredentialPresence(
        provider=provider,
        env_var=env_var,
        present_in_env=in_env,
        present_in_keychain=in_kc,
    )


def audit_credential_presence() -> list[dict[str, object]]:
    """Return redacted presence rows for all Probe providers."""
    return [
        credential_presence(p).to_audit_dict()
        for p in ("openrouter", "huggingface", "cursor")
    ]


__all__ = [
    "CredentialBoundaryError",
    "CredentialPresence",
    "ENV_OPENROUTER",
    "ENV_HUGGINGFACE",
    "ENV_HUGGINGFACE_ALT",
    "ENV_CURSOR",
    "KEYCHAIN_SERVICE",
    "assert_probe_credential_boundary",
    "audit_credential_presence",
    "credential_presence",
    "load_cursor_api_key",
    "load_huggingface_token",
    "load_openrouter_api_key",
    "load_provider_credential",
]
