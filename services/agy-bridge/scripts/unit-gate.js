#!/usr/bin/env node
"use strict";
const path = require("path");
const fs = require("fs");
const os = require("os");
process.env.COMPASS_CIRCUIT_CACHE = "/tmp/compass-circuits-test";
process.env.AGY_GATE_DEV = "1";
process.env.AGY_FAIL_OPEN = "1";
const gate = require("../src/circuitGate");
const DEMO_URL = "https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm";
const DEMO_SHA = "853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389";
const BAD_SHA = "0000000000000000000000000000000000000000000000000000000000000001";

(async () => {
  fs.rmSync(process.env.COMPASS_CIRCUIT_CACHE, { recursive: true, force: true });
  fs.mkdirSync(process.env.COMPASS_CIRCUIT_CACHE, { recursive: true });
  const body1 = { compass: { circuit: { url: DEMO_URL, sha256: DEMO_SHA, proof: { stub: true } } } };
  console.log("resolve1...");
  const r1 = await gate.runCircuitGate(body1);
  console.log("r1", r1);
  if (!r1.ok || r1.gate.sha256 !== DEMO_SHA || r1.gate.cached !== false) throw new Error("miss expected");
  console.log("resolve2...");
  const r2 = await gate.runCircuitGate(body1);
  console.log("r2", r2);
  if (!r2.ok || r2.gate.cached !== true) throw new Error("hit expected");
  console.log("bad digest...");
  let denied = false;
  try {
    await gate.runCircuitGate({ compass: { circuit: { url: DEMO_URL, sha256: BAD_SHA, proof: { stub: true } } } });
  } catch (e) {
    denied = e && e.status === 403;
    console.log("bad", e.status, e.code, e.message);
  }
  if (!denied) throw new Error("expected 403");
  console.log("UNIT_SMOKE_OK");
})().catch((e) => { console.error(e); process.exit(1); });
