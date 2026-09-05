"""Host ABI Protocol — storage / clock / log / config. No keys.* ever.

Browser builds must omit ``fetch``. See ``docs/abi/host-abi.v1.md`` and
``docs/abi/host-abi.v1.json``.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

LogLevel = Literal["debug", "info", "warn", "error"]

# Forbidden import namespace — must never appear on the WASM import table.
FORBIDDEN_HOST_NAMESPACES: tuple[str, ...] = ("keys",)

COMPASS_HOST_ABI = "1.0.0"
ABI_MIN = "1.0.0"
ABI_MAX = "1.999.0"


@runtime_checkable
class HostStorage(Protocol):
    def read_snapshot(self, agent_or_project_id: str) -> bytes:
        """Return graph snapshot bytes **without secrets**."""
        ...


@runtime_checkable
class HostClock(Protocol):
    def now_iso(self) -> str:
        """UTC ISO-8601 timestamp for validity filtering."""
        ...


@runtime_checkable
class HostLog(Protocol):
    def write(self, level: LogLevel, msg: str) -> None:
        """Rationale / errors only — never key material or forbidden prompts."""
        ...


@runtime_checkable
class HostConfig(Protocol):
    def get(self, key: str) -> Any:
        """Non-secret config (λ, default model id, abi_min/max)."""
        ...


@runtime_checkable
class HostABI(Protocol):
    """Full host import table for Wasmer instantiation."""

    storage: HostStorage
    clock: HostClock
    log: HostLog
    config: HostConfig
    # fetch: optional, native hosts only — intentionally absent from Protocol
    # so browser type-checkers cannot require it.


class InMemoryHost:
    """Test double: feeds a preloaded snapshot; records log lines."""

    def __init__(
        self,
        snapshot: bytes | None = None,
        *,
        config: dict[str, Any] | None = None,
        now: str = "1970-01-01T00:00:00Z",
    ) -> None:
        self._snapshot = snapshot
        self._config = dict(config or {})
        self._now = now
        self.logs: list[tuple[str, str]] = []

    # storage
    def read_snapshot(self, agent_or_project_id: str) -> bytes:
        _ = agent_or_project_id
        if self._snapshot is None:
            return b""
        return self._snapshot

    # clock
    def now_iso(self) -> str:
        return self._now

    # log
    def write(self, level: LogLevel, msg: str) -> None:
        self.logs.append((level, msg))

    # config
    def get(self, key: str) -> Any:
        return self._config.get(key)


def assert_no_key_material(payload: bytes | str | dict[str, Any]) -> None:
    """Guard used by tests: reject obvious secret field names in snapshot/config.

    Raises ``ValueError`` if forbidden keys appear. Hosts must strip secrets
    before ``storage.read_snapshot``.
    """
    forbidden_substrings = (
        "api_key",
        "apikey",
        "cursor_api_key",
        "openrouter",
        "authorization",
        "bearer ",
        "secret",
        "private_key",
    )
    if isinstance(payload, dict):
        text = str(payload).lower()
    elif isinstance(payload, bytes):
        text = payload.decode("utf-8", errors="replace").lower()
    else:
        text = str(payload).lower()
    for needle in forbidden_substrings:
        if needle in text:
            raise ValueError(f"forbidden key material marker in host payload: {needle!r}")
