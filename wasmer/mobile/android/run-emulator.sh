#!/usr/bin/env bash
# Android emulator/device run. Exit 2 = NOT_RUN (no SDK). Exit 1 = tests failed.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
OUT_DIR="${ARTIFACTS_DIR:-$REPO/test-results/s-desktop-mobile}"
mkdir -p "$OUT_DIR"
TS="$(date -u +%Y%m%d-%H%M%S)"
LOG="$OUT_DIR/mobile-android-$TS.log.txt"
JSON="$OUT_DIR/mobile-android.json"

{
  echo "=== comPASS Android host ==="
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} | tee "$LOG"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$SDK" && -d "${HOME}/Library/Android/sdk" ]]; then
  SDK="${HOME}/Library/Android/sdk"
fi

if [[ -z "$SDK" || ! -d "$SDK" ]]; then
  echo "[NOT_RUN] Android SDK not installed (ANDROID_HOME/ANDROID_SDK_ROOT unset; no Library/Android/sdk)" | tee -a "$LOG"
  echo "[NOT_RUN] Host sources exist at wasmer/mobile/android/ — assembleDebug and emulator API 34 are human follow-up." | tee -a "$LOG"
  python3 - "$JSON" <<'PY'
import json, sys
open(sys.argv[1], "w").write(json.dumps({
    "ok": False,
    "grade": "NOT_RUN",
    "reason": "Android SDK missing",
    "host": "android-webview",
    "device": False,
    "emulator": False,
    "compile": False,
}, indent=2) + "\n")
PY
  exit 2
fi

echo "ANDROID_SDK=$SDK" | tee -a "$LOG"
export ANDROID_HOME="$SDK"
export ANDROID_SDK_ROOT="$SDK"

if [[ ! -f "$HERE/local.properties" ]]; then
  printf 'sdk.dir=%s\n' "$SDK" > "$HERE/local.properties"
fi

"$HERE/../sync-assets.sh" 2>&1 | tee -a "$LOG"

if [[ ! -x "$HERE/gradlew" ]]; then
  echo "[NOT_RUN] gradlew missing" | tee -a "$LOG"
  echo '{"ok":false,"grade":"NOT_RUN","reason":"gradlew missing"}' > "$JSON"
  exit 2
fi

set +e
"$HERE/gradlew" --no-daemon assembleDebug 2>&1 | tee -a "$LOG"
ASM_RC=${PIPESTATUS[0]}
set -e
if [[ $ASM_RC -ne 0 ]]; then
  echo "[FAIL] assembleDebug exit=$ASM_RC" | tee -a "$LOG"
  echo "{\"ok\":false,\"grade\":\"FAIL\",\"reason\":\"assembleDebug\",\"exit\":$ASM_RC}" > "$JSON"
  exit 1
fi
echo "[PASS] assembleDebug" | tee -a "$LOG"

ADB="$SDK/platform-tools/adb"
if [[ ! -x "$ADB" ]]; then
  ADB="$(command -v adb || true)"
fi
DEVICES=""
if [[ -n "$ADB" ]]; then
  DEVICES="$("$ADB" devices 2>/dev/null | awk 'NR>1 && $2=="device"{print $1}')"
fi
if [[ -z "$DEVICES" ]]; then
  echo "[NOT_RUN] assembleDebug succeeded; no emulator/device online (adb devices empty)" | tee -a "$LOG"
  python3 - "$JSON" <<'PY'
import json, sys
open(sys.argv[1], "w").write(json.dumps({
    "ok": False,
    "grade": "NOT_RUN",
    "reason": "no emulator or device online after assembleDebug",
    "host": "android-webview",
    "device": False,
    "emulator": False,
    "compile": True,
}, indent=2) + "\n")
PY
  exit 2
fi

set +e
"$HERE/gradlew" --no-daemon connectedDebugAndroidTest 2>&1 | tee -a "$LOG"
TEST_RC=${PIPESTATUS[0]}
set -e
GRADE="FAIL"
OK=false
if [[ $TEST_RC -eq 0 ]]; then
  GRADE="PARTIAL"
  OK=true
  echo "[PASS] connectedDebugAndroidTest (emulator/device)" | tee -a "$LOG"
else
  echo "[FAIL] connectedDebugAndroidTest exit=$TEST_RC" | tee -a "$LOG"
fi
python3 - "$JSON" "$OK" "$GRADE" "$TEST_RC" <<'PY'
import json, sys
ok = sys.argv[2].lower() == "true"
open(sys.argv[1], "w").write(json.dumps({
    "ok": ok,
    "grade": sys.argv[3],
    "connectedDebugAndroidTest_exit": int(sys.argv[4]),
    "host": "android-webview",
    "device": False,
    "emulator": True,
    "compile": True,
}, indent=2) + "\n")
PY
exit $TEST_RC
