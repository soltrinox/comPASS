"""comPASS / compass-router — capability-aware model routing engine.

Three planes (see docs/ARCHITECTURE.md):
  Graph  — bitemporal capability store + bandit posterior (no provider keys)
  Probe  — native sidecar; holds credentials; NEVER on the prompt path
  Route  — classify → score → decide; fail-open; no provider keys

This package is the Track C sibling engine. It does not modify comPREssOR.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]

# Track D: WASM-safe read path lives in compass.core (see docs/WASMER.md).
