#!/usr/bin/env bash
# Boot an available iPhone simulator and run CompassMobileHostTests.
# Exit 2 if Xcode/simulator is missing (honest NOT_RUN). Exit 1 on test fail.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
OUT_DIR="${ARTIFACTS_DIR:-$REPO/test-results/s-desktop-mobile}"
mkdir -p "$OUT_DIR"

stamp() { date -u +%Y%m%d-%H%M%S; }
TS="$(stamp)"
LOG="$OUT_DIR/mobile-ios-simulator-$TS.log.txt"
JSON="$OUT_DIR/mobile-ios-simulator.json"

{
  echo "=== comPASS iOS simulator host ==="
  echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo-relative=wasmer/mobile/ios"
} | tee "$LOG"

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "[NOT_RUN] xcodebuild not on PATH" | tee -a "$LOG"
  echo '{"ok":false,"grade":"NOT_RUN","reason":"xcodebuild missing"}' > "$JSON"
  exit 2
fi
if ! command -v xcrun >/dev/null 2>&1; then
  echo "[NOT_RUN] xcrun not on PATH" | tee -a "$LOG"
  echo '{"ok":false,"grade":"NOT_RUN","reason":"xcrun missing"}' > "$JSON"
  exit 2
fi

echo "xcodebuild=$(xcodebuild -version 2>/dev/null | tr '\n' ' ')" | tee -a "$LOG"

"$HERE/../sync-assets.sh" 2>&1 | tee -a "$LOG"

if ! command -v xcodegen >/dev/null 2>&1; then
  if [[ ! -f "$HERE/CompassMobileHost.xcodeproj/project.pbxproj" ]]; then
    echo "[NOT_RUN] xcodegen missing and no generated xcodeproj" | tee -a "$LOG"
    echo '{"ok":false,"grade":"NOT_RUN","reason":"xcodegen missing"}' > "$JSON"
    exit 2
  fi
else
  (cd "$HERE" && xcodegen generate) 2>&1 | tee -a "$LOG"
fi

pick_udid() {
  python3 - <<'PY'
import json, subprocess, sys
raw = subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "-j"], text=True)
data = json.loads(raw)
preferred = []
fallback = []
for runtime, devices in data.get("devices", {}).items():
    for dev in devices:
        if not dev.get("isAvailable"):
            continue
        name = dev.get("name") or ""
        if "iPhone" not in name:
            continue
        rec = (runtime, name, dev.get("udid"))
        if "iOS-18" in runtime or "iOS 18" in runtime:
            preferred.append(rec)
        else:
            fallback.append(rec)
order = preferred + fallback
if not order:
    sys.exit(1)
runtime, name, udid = order[0]
print(udid)
print(name, file=sys.stderr)
print(runtime, file=sys.stderr)
PY
}

set +e
PICK="$(pick_udid 2>"$OUT_DIR/mobile-ios-sim-pick.err.txt")"
PICK_RC=$?
set -e
if [[ $PICK_RC -ne 0 || -z "${PICK:-}" ]]; then
  echo "[NOT_RUN] no available iPhone simulator" | tee -a "$LOG"
  cat "$OUT_DIR/mobile-ios-sim-pick.err.txt" >> "$LOG" || true
  echo '{"ok":false,"grade":"NOT_RUN","reason":"no iPhone simulator runtime"}' > "$JSON"
  exit 2
fi
UDID="$PICK"
echo "simulator_udid=$UDID" | tee -a "$LOG"
cat "$OUT_DIR/mobile-ios-sim-pick.err.txt" | tee -a "$LOG" || true

xcrun simctl boot "$UDID" 2>&1 | tee -a "$LOG" || true
xcrun simctl bootstatus "$UDID" -b 2>&1 | tee -a "$LOG"

BUNDLE_ID="org.compass.wasmer.mobilehost"
CFG_DIR="$HERE/build/Debug-iphonesimulator"
mkdir -p "$CFG_DIR"

echo "--- build -sdk iphonesimulator (no scheme destination; Xcode 26.2 may lack a matching runtime dest) ---" | tee -a "$LOG"
set +e
xcodebuild \
  -project "$HERE/CompassMobileHost.xcodeproj" \
  -target CompassMobileHost \
  -sdk iphonesimulator \
  -arch arm64 \
  -configuration Debug \
  CONFIGURATION_BUILD_DIR="$CFG_DIR" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  build \
  2>&1 | tee -a "$LOG"
BUILD_RC=${PIPESTATUS[0]}
set -e
if [[ $BUILD_RC -ne 0 ]]; then
  echo "[FAIL] simulator SDK build exit=$BUILD_RC" | tee -a "$LOG"
  echo "{\"ok\":false,\"grade\":\"FAIL\",\"reason\":\"xcodebuild build\",\"exit\":$BUILD_RC,\"simulator_udid\":\"$UDID\"}" > "$JSON"
  exit 1
fi

APP="$CFG_DIR/CompassMobileHost.app"
if [[ ! -d "$APP" ]]; then
  echo "[FAIL] missing $APP" | tee -a "$LOG"
  echo '{"ok":false,"grade":"FAIL","reason":"app bundle missing after build"}' > "$JSON"
  exit 1
fi
echo "[PASS] built $APP" | tee -a "$LOG"

xcrun simctl uninstall "$UDID" "$BUNDLE_ID" 2>/dev/null || true
xcrun simctl install "$UDID" "$APP" 2>&1 | tee -a "$LOG"
xcrun simctl launch "$UDID" "$BUNDLE_ID" 2>&1 | tee -a "$LOG"

echo "--- poll Documents/compass-parity.json ---" | tee -a "$LOG"
REPORT=""
for i in $(seq 1 45); do
  DATA="$(xcrun simctl get_app_container "$UDID" "$BUNDLE_ID" data 2>/dev/null || true)"
  CAND="${DATA:-}/Documents/compass-parity.json"
  if [[ -n "$DATA" && -f "$CAND" ]]; then
    REPORT="$CAND"
    echo "[PASS] result file after ${i}s: $CAND" | tee -a "$LOG"
    break
  fi
  sleep 2
done

python3 - "$LOG" "$JSON" "$UDID" "${REPORT:-}" <<'PY'
import json, os, sys
log_path, json_path, udid, report_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
report = None
if report_path and os.path.isfile(report_path):
    report = json.loads(open(report_path, encoding="utf-8").read())
ok = False
reason = None
if not report:
    reason = "WKWebView did not write compass-parity.json (timeout). Xcode 26.2 scheme destinations were unavailable; simctl install/launch was used."
    ok = False
else:
    cheap = (report.get("fixture_min") or {}).get("selected_model_version_id") == "urn:mg:model:cheap"
    miss = (report.get("missing") or {}).get("default_reason") == "snapshot_missing"
    ok = bool(report.get("ok")) and cheap and miss
    if not ok:
        reason = report.get("error") or "parity mismatch"
out = {
    "ok": ok,
    "grade": "PARTIAL" if ok else "FAIL",
    "simulator_udid": udid,
    "host": "ios-wkwebview-simulator",
    "device": False,
    "emulator": True,
    "run_path": "simctl-install-launch",
    "js_report": report,
    "reason": reason,
}
open(json_path, "w", encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
print(json.dumps({"ok": out["ok"], "grade": out["grade"]}))
sys.exit(0 if ok else 1)
PY
PY_RC=$?
echo "evidence_log=$LOG" | tee -a "$LOG"
echo "evidence_json=$JSON" | tee -a "$LOG"
exit "$PY_RC"
