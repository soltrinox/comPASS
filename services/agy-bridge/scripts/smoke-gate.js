#!/usr/bin/env node
"use strict";
const BASE = process.env.AGY_BRIDGE_URL || "http://127.0.0.1:8791";
const DEMO_URL = "https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm";
const DEMO_SHA = "853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389";
const BAD_SHA = "0000000000000000000000000000000000000000000000000000000000000001";

async function post(circuit) {
  const body = {
    model: "agy",
    messages: [{ role: "user", content: "reply with exactly: pong" }],
    compass: { circuit },
  };
  const res = await fetch(BASE + "/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch (_) { json = { raw: text }; }
  return { status: res.status, json };
}

(async () => {
  const hz = await fetch(BASE + "/healthz");
  if (!hz.ok) { console.error("healthz failed", hz.status); process.exit(1); }
  console.log("healthz ok");
  const circuitGood = { url: DEMO_URL, sha256: DEMO_SHA, proof: { stub: true } };
  console.log("--- request 1 ---");
  const r1 = await post(circuitGood);
  console.log(JSON.stringify({ status: r1.status, gate: r1.json.compass && r1.json.compass.gate, err: r1.json.error }, null, 2));
  if (r1.status !== 200) { console.error("FAIL r1"); process.exit(1); }
  if (!r1.json.compass || r1.json.compass.gate.sha256 !== DEMO_SHA) { console.error("FAIL sha", r1.json.compass); process.exit(1); }
  console.log("--- request 2 (cache hit) ---");
  const r2 = await post(circuitGood);
  console.log(JSON.stringify({ status: r2.status, gate: r2.json.compass && r2.json.compass.gate }, null, 2));
  if (r2.status !== 200 || !r2.json.compass.gate.cached) { console.error("FAIL r2 cache", r2.json.compass); process.exit(1); }
  console.log("--- request 3 (bad digest 403) ---");
  const r3 = await post({ url: DEMO_URL, sha256: BAD_SHA, proof: { stub: true } });
  console.log(JSON.stringify({ status: r3.status, error: r3.json.error, compass: r3.json.compass }, null, 2));
  if (r3.status !== 403) { console.error("FAIL r3 expected 403"); process.exit(1); }
  console.log("SMOKE_OK");
})().catch((e) => { console.error(e); process.exit(1); });
