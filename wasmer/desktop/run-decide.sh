#!/usr/bin/env bash
# Packaged desktop Wasmer entrypoint for compass-decide.wasm (Track J).
# Beyond raw wasm bytes: volume map, fixture default, fail-open demos, exit codes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WASM="${COMPASS_DECIDE_WASM:-$ROOT/wasmer/artifacts/compass-decide.wasm}"
FIXTURE="${COMPASS_SNAPSHOT:-$ROOT/wasmer/fixtures/snapshot_min.json}"
REQUEST="${COMPASS_REQUEST:-implement a function}"
NOW="${COMPASS_NOW:-2026-09-05T00:00:00Z}"
DEMO="${COMPASS_FAIL_OPEN_DEMO:-}"

if ! command -v wasmer >/dev/null 2>&1; then
  echo "error: wasmer CLI not on PATH (brew install wasmer)" >&2
  exit 127
fi
if [[ ! -f "$WASM" ]]; then
  echo "error: missing wasm: $WASM" >&2
  exit 2
fi

VOL_ARGS=(--volume "$ROOT/wasmer:/wasmer")
ARGS=(--request "$REQUEST" --now "$NOW")
if [[ -n "$DEMO" ]]; then
  ARGS+=(--fail-open-demo "$DEMO")
else
  # Guest path under preopened /wasmer
  GUEST="/wasmer/fixtures/$(basename "$FIXTURE")"
  # If fixture is not under wasmer/fixtures, copy hint:
  if [[ ! -f "$ROOT/wasmer/fixtures/$(basename "$FIXTURE")" ]]; then
    echo "error: snapshot must live under wasmer/fixtures for volume map (got $FIXTURE)" >&2
    exit 2
  fi
  ARGS+=(--snapshot "$GUEST")
fi

exec wasmer run "$WASM" "${VOL_ARGS[@]}" -- "${ARGS[@]}"
