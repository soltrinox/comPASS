#!/usr/bin/env bash
# Packaged desktop Wasmer entrypoint for compass-decide (Track J / plan B3).
#
# Execution order:
#   1. Registry by name/version — only when requested (COMPASS_WASMER_USE_REGISTRY=1
#      or --registry) AND a package name/version is set. Today this fails:
#      publish is NOT_RUN (wasmer/PUBLISH-NOT_RUN.md). Catch, log honestly, fall through.
#   2. Local .webc by path (default). Build with `wasmer package build` if missing.
#   3. Air-gap fallback: wasmer/artifacts/compass-decide.wasm (audit §A6 item 11).
#
# Guest args and `--volume "$ROOT/wasmer:/wasmer"` stay compatible with the
# raw-wasm invocation in scripts/wasmer_parity.py. That script still shells
# `wasmer run` on the loose artifact; this script's step 3 is the same mapping.
# Isolate a hop with COMPASS_DECIDE_SOURCE=registry|webc|wasm.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MANIFEST="$ROOT/wasmer.toml"
WASM_REL="wasmer/artifacts/compass-decide.wasm"
WASM="${COMPASS_DECIDE_WASM:-$ROOT/$WASM_REL}"
FIXTURE="${COMPASS_SNAPSHOT:-$ROOT/wasmer/fixtures/snapshot_min.json}"
REQUEST="${COMPASS_REQUEST:-implement a function}"
NOW="${COMPASS_NOW:-2026-09-05T00:00:00Z}"
DEMO="${COMPASS_FAIL_OPEN_DEMO:-}"
SOURCE="${COMPASS_DECIDE_SOURCE:-}"
USE_REGISTRY="${COMPASS_WASMER_USE_REGISTRY:-}"
REGISTRY_ONLY="${COMPASS_WASMER_REGISTRY_ONLY:-}"

log() { printf '%s\n' "$*" >&2; }

truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

relpath() {
  local p="$1"
  if [[ "$p" == "$ROOT"/* ]]; then
    printf '%s\n' "${p#"$ROOT"/}"
  else
    printf '%s\n' "$p"
  fi
}

toml_get() {
  local key="$1"
  awk -F'"' -v k="$key" '$0 ~ "^" k " *=" { print $2; exit }' "$MANIFEST"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry)
      USE_REGISTRY=1
      shift
      ;;
    --source)
      SOURCE="${2:-}"
      shift 2
      ;;
    --source=*)
      SOURCE="${1#*=}"
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      log "error: unknown flag $1 (supported: --registry, --source registry|webc|wasm)"
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ -n "${1:-}" ]]; then
  log "error: unexpected argument: $1"
  exit 2
fi

if ! command -v wasmer >/dev/null 2>&1; then
  log "error: wasmer CLI not on PATH (brew install wasmer)"
  exit 127
fi

if [[ ! -f "$MANIFEST" ]]; then
  log "error: missing package manifest: wasmer.toml"
  exit 2
fi

PKG_NAME="${COMPASS_WASMER_PACKAGE:-$(toml_get name)}"
PKG_VERSION="${COMPASS_WASMER_VERSION:-$(toml_get version)}"
PKG_REF="${COMPASS_WASMER_REF:-}"
if [[ -z "$PKG_REF" && -n "$PKG_NAME" && -n "$PKG_VERSION" ]]; then
  PKG_REF="${PKG_NAME}@${PKG_VERSION}"
fi

WEBC_DEFAULT="$ROOT/${PKG_NAME//\//-}-${PKG_VERSION}.webc"
WEBC="${COMPASS_WASMER_WEBC:-$WEBC_DEFAULT}"

VOL_ARGS=(--volume "$ROOT/wasmer:/wasmer")
ARGS=(--request "$REQUEST" --now "$NOW")
if [[ -n "$DEMO" ]]; then
  ARGS+=(--fail-open-demo "$DEMO")
else
  GUEST="/wasmer/fixtures/$(basename "$FIXTURE")"
  if [[ ! -f "$ROOT/wasmer/fixtures/$(basename "$FIXTURE")" ]]; then
    log "error: snapshot must live under wasmer/fixtures for volume map (got $(relpath "$FIXTURE"))"
    exit 2
  fi
  ARGS+=(--snapshot "$GUEST")
fi

# stdout = decide envelope only. Diagnostics go to stderr (do not redirect
# wasmer's stderr to a regular file — 7.4.0 swallows the diagnostic there).
try_run() {
  local label="$1"
  local input="$2"
  shift 2
  local extra=("$@")
  local rc
  log "[run-decide] source=${label} input=$(relpath "$input")"
  set +e
  wasmer --color never run "$input" "${extra[@]}" -- "${ARGS[@]}"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    return 0
  fi
  log "[run-decide] source=${label} failed rc=${rc} input=$(relpath "$input")"
  return "$rc"
}

ensure_webc() {
  if [[ -f "$WEBC" ]]; then
    log "[run-decide] using existing webc $(relpath "$WEBC")"
    return 0
  fi
  log "[run-decide] building local package: wasmer package build -o $(relpath "$WEBC") ."
  set +e
  (cd "$ROOT" && wasmer --color never package build --quiet -o "$WEBC" .) >&2
  local rc=$?
  set -e
  if [[ $rc -ne 0 || ! -f "$WEBC" ]]; then
    log "[run-decide] webc build failed rc=${rc}"
    return 1
  fi
  return 0
}

run_registry() {
  if [[ -z "$PKG_REF" ]]; then
    log "[run-decide] registry requested but package name/version is unset; skipping"
    return 1
  fi
  log "[run-decide] trying registry-by-name: wasmer run ${PKG_REF}"
  log "[run-decide] publish state is NOT_RUN until wasmer/PUBLISH-NOT_RUN.md flips; this hop is expected to fail until a human wasmer login + namespace claim + wasmer publish ."
  if try_run registry "$PKG_REF" "${VOL_ARGS[@]}"; then
    return 0
  fi
  log "[run-decide] registry-by-name PARTIAL (code present) / runtime NOT_RUN: ${PKG_REF} is not on the registry. Falling through. See wasmer/PUBLISH-NOT_RUN.md."
  return 1
}

run_webc() {
  if ! ensure_webc; then
    return 1
  fi
  # --offline: never resolve from the registry. Volume overlay keeps host
  # wasmer/fixtures in sync with scripts/wasmer_parity.py and the bundled [fs] map.
  try_run webc "$WEBC" --offline "${VOL_ARGS[@]}"
}

run_wasm() {
  if [[ ! -f "$WASM" ]]; then
    log "error: missing wasm: $(relpath "$WASM")"
    return 2
  fi
  try_run wasm "$WASM" --offline "${VOL_ARGS[@]}"
}

want_registry=0
if truthy "$USE_REGISTRY" || [[ "$SOURCE" == "registry" ]]; then
  want_registry=1
fi

case "$SOURCE" in
  ""|registry|webc|wasm) ;;
  *)
    log "error: COMPASS_DECIDE_SOURCE / --source must be registry, webc, or wasm (got ${SOURCE})"
    exit 2
    ;;
esac

if [[ "$SOURCE" == "wasm" ]]; then
  run_wasm
  exit $?
fi

if [[ "$SOURCE" == "webc" ]]; then
  run_webc
  exit $?
fi

if [[ "$want_registry" -eq 1 ]]; then
  if run_registry; then
    exit 0
  fi
  if truthy "$REGISTRY_ONLY"; then
    log "[run-decide] COMPASS_WASMER_REGISTRY_ONLY=1 — not falling through"
    exit 1
  fi
fi

if [[ "$SOURCE" == "registry" ]]; then
  # SOURCE=registry already attempted above; without REGISTRY_ONLY, fall through.
  :
fi

if run_webc; then
  exit 0
fi
log "[run-decide] falling through to air-gap wasm $(relpath "$WASM")"
run_wasm
exit $?
