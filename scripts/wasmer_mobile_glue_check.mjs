#!/usr/bin/env node
/**
 * Shared-glue check (NOT a mobile emulator/device run).
 * Instantiates compass_core_bg.wasm with the same host.js the iOS/Android
 * WebViews load, verifies SHA-256 against SHA256SUMS, and asserts
 * fixture_min → urn:mg:model:cheap and missing → snapshot_missing.
 */
import { createHash, webcrypto } from "node:crypto";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ART = join(ROOT, "wasmer", "artifacts");
const SUMS = join(ART, "SHA256SUMS");
const WASM = join(ART, "compass_core_bg.wasm");
const FIXTURE = join(ROOT, "wasmer", "fixtures", "snapshot_min.json");
const HOST_JS = join(ROOT, "wasmer", "mobile", "shared", "host.js");
const PIN = join(ROOT, "wasmer", "mobile", "shared", "EXPECTED_SHA256");

function sumsLine(text, name) {
  for (const line of text.split("\n")) {
    const t = line.trim();
    if (!t) continue;
    const [digest, file] = t.split(/\s+/, 2);
    if (file === name) return digest.toLowerCase();
  }
  return null;
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}-${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}`;
}

async function main() {
  const wasm = readFileSync(WASM);
  const expected = sumsLine(readFileSync(SUMS, "utf8"), "compass_core_bg.wasm");
  const pin = readFileSync(PIN, "utf8").trim().toLowerCase();
  const actual = createHash("sha256").update(wasm).digest("hex");
  const snapshotJson = readFileSync(FIXTURE, "utf8");

  const evidence = {
    kind: "mobile-shared-glue",
    not_a_device_run: true,
    artifact: "wasmer/artifacts/compass_core_bg.wasm",
    expected_sha256: expected,
    pin_file: pin,
    actual_sha256: actual,
    size_bytes: wasm.length,
    ok: false,
    glue: null,
    error: null,
  };

  if (!expected) {
    evidence.error = "SHA256SUMS missing compass_core_bg.wasm";
  } else if (actual !== expected) {
    evidence.error = `artifact digest mismatch expected=${expected} actual=${actual}`;
  } else if (pin !== expected) {
    evidence.error = `EXPECTED_SHA256 (${pin}) != SHA256SUMS (${expected})`;
  } else {
    const ctx = {
      console,
      WebAssembly,
      TextEncoder,
      TextDecoder,
      Uint8Array,
      ArrayBuffer,
      Int8Array,
      Uint16Array,
      Int16Array,
      Uint32Array,
      Int32Array,
      Float32Array,
      Float64Array,
      DataView,
      JSON,
      Promise,
      Error,
      Object,
      String,
      Number,
      Array,
      Boolean,
      Math,
      Date,
      parseInt,
      parseFloat,
      isNaN,
      isFinite,
      undefined,
      atob: (s) => Buffer.from(s, "base64").toString("latin1"),
      crypto: webcrypto,
      setTimeout,
      clearTimeout,
      queueMicrotask,
    };
    ctx.globalThis = ctx;
    vm.createContext(ctx);
    vm.runInContext(readFileSync(HOST_JS, "utf8"), ctx, { filename: "host.js" });
    const glue = ctx.CompassMobileHost;
    evidence.glue = await glue.runFromBytes(wasm, {
      expectedSha256: expected,
      snapshotJson,
      nowIso: glue.NOW_ISO,
      requireJsDigest: true,
    });
    evidence.ok = !!(evidence.glue && evidence.glue.ok);
    if (!evidence.ok) evidence.error = evidence.glue && evidence.glue.error;
  }

  const outDir = join(ROOT, "test-results", "s-desktop-mobile");
  mkdirSync(outDir, { recursive: true });
  const ts = stamp();
  const jsonPath = join(outDir, "mobile-glue-check.json");
  const logPath = join(outDir, `mobile-glue-check-${ts}.log.txt`);
  const body = JSON.stringify(evidence, null, 2) + "\n";
  writeFileSync(jsonPath, body);
  writeFileSync(logPath, body);

  const fixtureId = evidence.glue && evidence.glue.fixture_min && evidence.glue.fixture_min.selected_model_version_id;
  const missingReason = evidence.glue && evidence.glue.missing && evidence.glue.missing.default_reason;
  console.log(`[${evidence.ok ? "PASS" : "FAIL"}] mobile shared glue (Node, not emulator)`);
  console.log(`digest ${actual} match=${actual === expected}`);
  console.log(`fixture_min selected=${fixtureId}`);
  console.log(`missing default_reason=${missingReason}`);
  console.log(`evidence ${jsonPath}`);
  if (!evidence.ok) {
    console.error(evidence.error || "glue returned ok=false");
    process.exit(1);
  }
}

await main();
