#!/usr/bin/env bash
# Orchestrate B4 mobile hosts: glue check, size budget, iOS simulator, Android.
# Does not fake green. Missing emulator/SDK → NOT_RUN (exit 2 from child is allowed).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
OUT_DIR="${ARTIFACTS_DIR:-$REPO/test-results/s-desktop-mobile}"
mkdir -p "$OUT_DIR"
TS="$(date -u +%Y%m%d-%H%M%S)"
LOG="$OUT_DIR/mobile-hosts-$TS.log.txt"

exec > >(tee "$LOG") 2>&1

echo "=== comPASS mobile hosts ==="
echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "$REPO"
chmod +x "$HERE/sync-assets.sh" \
  "$HERE/ios/run-simulator.sh" \
  "$HERE/android/run-emulator.sh" \
  "$REPO/scripts/validate-wasmer-mobile.sh" \
  "$REPO/scripts/wasmer_mobile_glue_check.mjs" 2>/dev/null || true

echo "--- size budget ---"
python3 "$REPO/scripts/wasmer_size_budget.py"
echo "[PASS] size budget (browser cdylib shared with mobile)"

echo "--- shared glue (Node; not a device run) ---"
node "$REPO/scripts/wasmer_mobile_glue_check.mjs"

IOS_GRADE="NOT_RUN"
AND_GRADE="NOT_RUN"
set +e
"$HERE/ios/run-simulator.sh"
IOS_RC=$?
set -e
if [[ $IOS_RC -eq 0 ]]; then
  IOS_GRADE="PARTIAL"
  echo "[PASS] iOS simulator"
elif [[ $IOS_RC -eq 2 ]]; then
  echo "[NOT_RUN] iOS simulator skipped/unavailable"
else
  echo "[FAIL] iOS simulator tests"
fi

set +e
"$HERE/android/run-emulator.sh"
AND_RC=$?
set -e
if [[ $AND_RC -eq 0 ]]; then
  AND_GRADE="PARTIAL"
  echo "[PASS] Android emulator/device"
elif [[ $AND_RC -eq 2 ]]; then
  echo "[NOT_RUN] Android SDK/emulator unavailable"
else
  echo "[FAIL] Android host"
fi

python3 - "$OUT_DIR/mobile-hosts-summary.json" "$IOS_GRADE" "$AND_GRADE" "$IOS_RC" "$AND_RC" <<'PY'
import json, sys
ios_g, and_g, ios_rc, and_rc = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
# FULL requires a physical device log — this runner never claims FULL.
overall = "NOT_RUN"
if ios_g == "PARTIAL" or and_g == "PARTIAL":
    overall = "PARTIAL"
if ios_rc not in (0, 2) or and_rc not in (0, 2):
    overall = "FAIL"
open(sys.argv[1], "w").write(json.dumps({
    "overall": overall,
    "full_requires_physical_device": True,
    "ios": {"grade": ios_g, "exit": ios_rc},
    "android": {"grade": and_g, "exit": and_rc},
    "shared_glue": "see mobile-glue-check.json",
}, indent=2) + "\n")
print("overall", overall)
PY

# Fail the script only on hard FAIL (not NOT_RUN).
if [[ $IOS_RC -ne 0 && $IOS_RC -ne 2 ]]; then
  exit "$IOS_RC"
fi
if [[ $AND_RC -ne 0 && $AND_RC -ne 2 ]]; then
  exit "$AND_RC"
fi
echo "log=$LOG"
exit 0
