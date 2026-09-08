#!/usr/bin/env bash
# Copy compass_core_bg.wasm into mobile host asset dirs after verifying SHA256SUMS.
# No machine-absolute paths. Safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
ART="$REPO/wasmer/artifacts"
SUMS="$ART/SHA256SUMS"
WASM="$ART/compass_core_bg.wasm"
FIXTURE="$REPO/wasmer/fixtures/snapshot_min.json"
PIN="$HERE/shared/EXPECTED_SHA256"

if [[ ! -f "$WASM" ]]; then
  echo "[FAIL] missing $WASM (repo-relative wasmer/artifacts/compass_core_bg.wasm)" >&2
  exit 1
fi
if [[ ! -f "$SUMS" ]]; then
  echo "[FAIL] missing $SUMS" >&2
  exit 1
fi
if [[ ! -f "$FIXTURE" ]]; then
  echo "[FAIL] missing $FIXTURE" >&2
  exit 1
fi

EXPECTED="$(awk '$2 == "compass_core_bg.wasm" { print $1; exit }' "$SUMS")"
if [[ -z "$EXPECTED" ]]; then
  echo "[FAIL] SHA256SUMS has no compass_core_bg.wasm line" >&2
  exit 1
fi

if command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$WASM" | awk '{print $1}')"
else
  ACTUAL="$(sha256sum "$WASM" | awk '{print $1}')"
fi

if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "[FAIL] digest mismatch compass_core_bg.wasm expected=$EXPECTED actual=$ACTUAL" >&2
  exit 1
fi

PINNED="$(tr -d '[:space:]' < "$PIN")"
if [[ "$PINNED" != "$EXPECTED" ]]; then
  echo "[FAIL] shared/EXPECTED_SHA256 ($PINNED) != SHA256SUMS ($EXPECTED)" >&2
  exit 1
fi

SIZE="$(wc -c < "$WASM" | tr -d ' ')"
echo "[PASS] compass_core_bg.wasm sha256=$ACTUAL size=$SIZE"

# shared/ already holds host.js, index.html, EXPECTED_SHA256 — only drop wasm + fixture.
mkdir -p "$HERE/shared"
cp "$WASM" "$HERE/shared/compass_core_bg.wasm"
cp "$FIXTURE" "$HERE/shared/snapshot_min.json"

copy_one() {
  local dest_dir="$1"
  mkdir -p "$dest_dir"
  cp "$WASM" "$dest_dir/compass_core_bg.wasm"
  cp "$FIXTURE" "$dest_dir/snapshot_min.json"
  cp "$PIN" "$dest_dir/EXPECTED_SHA256"
  cp "$HERE/shared/host.js" "$dest_dir/host.js"
  cp "$HERE/shared/index.html" "$dest_dir/index.html"
}

copy_one "$HERE/ios/Resources"
copy_one "$HERE/android/app/src/main/assets"

echo "[PASS] synced wasm + fixture into shared/, ios/Resources/, android/app/src/main/assets/"
