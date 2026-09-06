/**
 * ENI6MA circuit Gate for agy-bridge.
 *
 * Resolve / pin / cache WASM circuits, fail-closed on digest mismatch,
 * then validate via compile + ABI probe (DEMO-MINT is wasm-bindgen /
 * build_minimal_proof — no freestanding verify yet).
 *
 * See docs/CIRCUIT-ABI.md, docs/adr/0007-agy-behind-eni6ma-gate.md, README.md.
 */

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const fsp = require("fs").promises;
const os = require("os");
const path = require("path");
const { URL } = require("url");

const ALLOWED_HOSTS = new Set(["raw.githubusercontent.com", "github.com"]);

/** Names that look like challenge / verify / prove APIs (case-insensitive). */
const VERIFY_LIKE = /^(verify|validate|check_proof|verify_proof|check)$/i;
const CHALLENGE_LIKE = /^(challenge|new_challenge|create_challenge|get_challenge)$/i;
const PROVE_LIKE = /^(prove|build_minimal_proof|build_proof|generate_proof|mint_proof)$/i;

/** Cache root: COMPASS_CIRCUIT_CACHE or ~/.compass/circuits/ */
function cacheDir() {
  const env = process.env.COMPASS_CIRCUIT_CACHE;
  if (env && String(env).trim()) return path.resolve(String(env).trim());
  return path.join(os.homedir(), ".compass", "circuits");
}

function urlIndexPath(dir) {
  return path.join(dir, "url-index.json");
}

async function ensureCacheDir(dir) {
  await fsp.mkdir(dir, { recursive: true });
}

async function readUrlIndex(dir) {
  const p = urlIndexPath(dir);
  try {
    const raw = await fsp.readFile(p, "utf8");
    const j = JSON.parse(raw);
    return j && typeof j === "object" ? j : {};
  } catch (_) {
    return {};
  }
}

async function writeUrlIndex(dir, index) {
  const p = urlIndexPath(dir);
  const tmp = p + ".tmp";
  await fsp.writeFile(tmp, JSON.stringify(index, null, 2) + "\n", "utf8");
  await fsp.rename(tmp, p);
}

function sha256Hex(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex");
}

/**
 * Normalize github.com/blob/... → raw.githubusercontent.com/...
 * Leave raw.githubusercontent.com unchanged.
 */
function normalizeCircuitUrl(input) {
  if (!input || typeof input !== "string") {
    throw Object.assign(new Error("circuit.url is required"), { code: "circuit_url_required", status: 400 });
  }
  let u;
  try {
    u = new URL(input.trim());
  } catch (_) {
    throw Object.assign(new Error("circuit.url is not a valid URL"), { code: "circuit_url_invalid", status: 400 });
  }
  if (u.protocol !== "https:") {
    throw Object.assign(new Error("circuit.url must be https"), { code: "circuit_url_scheme", status: 403 });
  }
  const host = u.hostname.toLowerCase();
  if (!ALLOWED_HOSTS.has(host)) {
    throw Object.assign(
      new Error(`circuit.url host not allowlisted: ${host} (allowed: raw.githubusercontent.com, github.com)`),
      { code: "circuit_host_denied", status: 403 }
    );
  }
  if (host === "github.com") {
    const parts = u.pathname.split("/").filter(Boolean);
    const blobIdx = parts.indexOf("blob");
    if (blobIdx >= 2 && parts.length > blobIdx + 2) {
      const owner = parts[0];
      const repo = parts[1];
      const ref = parts[blobIdx + 1];
      const filePath = parts.slice(blobIdx + 2).join("/");
      return `https://raw.githubusercontent.com/${owner}/${repo}/${ref}/${filePath}`;
    }
    throw Object.assign(
      new Error("github.com circuit.url must be a /blob/ URL (or use raw.githubusercontent.com)"),
      { code: "circuit_url_unsupported", status: 400 }
    );
  }
  return u.toString();
}

function parseSha256Sidecar(text) {
  if (!text || typeof text !== "string") return null;
  const line = text.trim().split(/\r?\n/)[0] || "";
  const m = line.match(/^([a-fA-F0-9]{64})\b/);
  return m ? m[1].toLowerCase() : null;
}

function normalizeClientSha(sha) {
  if (sha == null || sha === "") return null;
  const s = String(sha).trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(s)) {
    throw Object.assign(new Error("circuit.sha256 must be 64 hex chars"), {
      code: "circuit_sha256_invalid",
      status: 400,
    });
  }
  return s;
}

function envTruthy(name) {
  const v = String(process.env[name] || "").toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}

function envFalsyDefaultTrue(name) {
  // AGY_FAIL_OPEN defaults to "1" (truthy) when unset
  const raw = process.env[name];
  if (raw == null || raw === "") return true;
  const v = String(raw).toLowerCase();
  return v !== "0" && v !== "false" && v !== "no";
}

async function fetchBytes(url, { timeoutMs = 60000 } = {}) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: "GET",
      redirect: "follow",
      signal: ctrl.signal,
      headers: { Accept: "application/wasm,*/*" },
    });
    if (!res.ok) {
      const err = new Error(`fetch ${url} failed: HTTP ${res.status}`);
      err.code = "circuit_fetch_failed";
      err.status = 403;
      throw err;
    }
    const ab = await res.arrayBuffer();
    return Buffer.from(ab);
  } catch (e) {
    if (e && e.code) throw e;
    const err = new Error(`fetch ${url} failed: ${e && e.message ? e.message : e}`);
    err.code = "circuit_fetch_failed";
    err.status = 403;
    throw err;
  } finally {
    clearTimeout(t);
  }
}

async function fetchSidecarSha(wasmUrl) {
  try {
    const buf = await fetchBytes(wasmUrl + ".sha256", { timeoutMs: 15000 });
    return parseSha256Sidecar(buf.toString("utf8"));
  } catch (_) {
    return null;
  }
}

function isWbindgenNoise(name) {
  return (
    name.startsWith("__wbindgen") ||
    name.startsWith("__wbg_") ||
    name.startsWith("__externref_") ||
    name === "__abort_handler" ||
    name === "__instance_terminated" ||
    name === "__data_end" ||
    name === "__heap_base"
  );
}

/**
 * Inventory exports/imports and classify known API shapes.
 */
function probeAbi(mod) {
  const exportsList = WebAssembly.Module.exports(mod).map((e) => ({
    name: e.name,
    kind: e.kind,
  }));
  const importsList = WebAssembly.Module.imports(mod).map((i) => ({
    module: i.module,
    name: i.name,
    kind: i.kind,
  }));

  const meaningful = exportsList.filter((e) => !isWbindgenNoise(e.name));
  const exportNames = exportsList.map((e) => e.name);
  const verifyExports = exportNames.filter((n) => VERIFY_LIKE.test(n));
  const challengeExports = exportNames.filter((n) => CHALLENGE_LIKE.test(n));
  const proveExports = exportNames.filter((n) => PROVE_LIKE.test(n));
  const hasBuildMinimalProof = exportNames.includes("build_minimal_proof");
  const wbindgen = importsList.some(
    (i) =>
      i.module === "__wbindgen_placeholder__" ||
      i.module === "__wbindgen_externref_xform__" ||
      i.module.startsWith("__wbindgen")
  );

  let shape = "opaque";
  if (verifyExports.length && challengeExports.length) shape = "challenge_verify";
  else if (verifyExports.length) shape = "verify";
  else if (proveExports.length || hasBuildMinimalProof) shape = "prove_only";
  else if (wbindgen) shape = "wbindgen_opaque";

  return {
    export_count: exportsList.length,
    import_count: importsList.length,
    meaningful_exports: meaningful,
    verify_exports: verifyExports,
    challenge_exports: challengeExports,
    prove_exports: proveExports,
    has_build_minimal_proof: hasBuildMinimalProof,
    wbindgen,
    shape,
    import_modules: [...new Set(importsList.map((i) => i.module))],
  };
}

/**
 * Minimal stub import object so wasm-bindgen modules can soft-instantiate.
 * Does not implement a real proof API — only load/ABI probe.
 */
function stubWbindgenImports(mod) {
  const imports = WebAssembly.Module.imports(mod);
  const tables = {};
  const out = {};

  for (const imp of imports) {
    if (!out[imp.module]) out[imp.module] = {};
    if (imp.kind === "function") {
      out[imp.module][imp.name] = function stubFn() {
        // describe / table helpers often need numeric returns
        if (/grow/i.test(imp.name)) return 0;
        if (/describe_cast/i.test(imp.name)) return 0;
        if (/clone_ref|new_/i.test(imp.name)) return 0;
        return undefined;
      };
    } else if (imp.kind === "table") {
      if (!tables[imp.module]) {
        tables[imp.module] = new WebAssembly.Table({ initial: 128, element: "anyfunc" });
      }
      out[imp.module][imp.name] = tables[imp.module];
    } else if (imp.kind === "memory") {
      out[imp.module][imp.name] = new WebAssembly.Memory({ initial: 256 });
    } else if (imp.kind === "global") {
      out[imp.module][imp.name] = new WebAssembly.Global({ value: "i32", mutable: true }, 0);
    }
  }

  // externref table commonly required by wbindgen
  if (out.__wbindgen_externref_xform__ && !out.__wbindgen_externref_xform__.__wbindgen_externref_table) {
    try {
      out.wbg = out.wbg || {};
      if (!out.wbg.__wbindgen_export_0) {
        // some builds expect an externref table via export after instantiate
      }
    } catch (_) {}
  }
  return out;
}

async function softInstantiate(mod) {
  // 1) empty imports
  try {
    const inst = await WebAssembly.instantiate(mod, {});
    return { ok: true, mode: "empty_imports", instance: inst };
  } catch (e1) {
    // 2) stub wbindgen
    try {
      const imports = stubWbindgenImports(mod);
      const inst = await WebAssembly.instantiate(mod, imports);
      return { ok: true, mode: "stub_wbindgen", instance: inst };
    } catch (e2) {
      return {
        ok: false,
        mode: "instantiate_failed",
        error: (e2 && e2.message) || (e1 && e1.message) || String(e2 || e1),
      };
    }
  }
}

function hasNonEmptyProof(proof, challengeId) {
  return (
    (typeof proof === "string" && proof.trim().length > 0) ||
    (proof && typeof proof === "object" && !Array.isArray(proof) && Object.keys(proof).length > 0) ||
    (typeof challengeId === "string" && challengeId.trim().length > 0)
  );
}

/**
 * ENI6MA validate — digest already checked by resolveCircuit.
 * DEMO-MINT: compile + abi_probe; wire verify when exports allow; else two-tier modes.
 */
async function eni6maValidate(wasmBytes, proof, challengeId) {
  let mod;
  try {
    mod = await WebAssembly.compile(wasmBytes);
  } catch (e) {
    return {
      ok: false,
      reason: `wasm_compile_failed: ${e && e.message ? e.message : e}`,
      abi: null,
      instantiate: null,
    };
  }

  const abi = probeAbi(mod);
  const inst = await softInstantiate(mod);

  // If verify-shaped exports exist, attempt a best-effort call (future-proof).
  if (abi.verify_exports.length && inst.ok && inst.instance) {
    const exp = inst.instance.exports;
    const name = abi.verify_exports[0];
    const fn = exp[name];
    if (typeof fn === "function") {
      try {
        // Unknown signature — do not pass untrusted buffers blindly.
        // Record presence only; treat as probe until ABI is documented.
        return {
          ok: true,
          reason: "verify_export_present_unwired",
          abi,
          instantiate: { ok: true, mode: inst.mode },
          wired: false,
          verify_export: name,
        };
      } catch (e) {
        return {
          ok: false,
          reason: `verify_call_failed: ${e && e.message ? e.message : e}`,
          abi,
          instantiate: { ok: true, mode: inst.mode },
        };
      }
    }
  }

  const proofOk = hasNonEmptyProof(proof, challengeId);

  return {
    ok: true,
    reason: abi.has_build_minimal_proof
      ? "abi_probe_build_minimal_proof"
      : "abi_probe",
    abi,
    instantiate: {
      ok: !!inst.ok,
      mode: inst.mode,
      error: inst.error || null,
    },
    proof_present: proofOk,
    wired: false,
  };
}

async function validateProof(wasmBytes, circuit) {
  const proof = circuit && circuit.proof;
  const challengeId = circuit && (circuit.challenge_id || circuit.challengeId);
  const hasProof = hasNonEmptyProof(proof, challengeId);

  const gateDev = envTruthy("AGY_GATE_DEV");
  const gateStrict = envTruthy("AGY_GATE_STRICT");
  const failOpenGate = envFalsyDefaultTrue("AGY_FAIL_OPEN");

  const result = await eni6maValidate(wasmBytes, proof, challengeId);
  if (!result.ok && result.reason && result.reason.startsWith("wasm_compile_failed")) {
    return {
      ok: false,
      mode: "validate_failed",
      reason: result.reason,
      validated: false,
      abi: result.abi,
    };
  }

  const abiSummary = result.abi
    ? {
        shape: result.abi.shape,
        export_count: result.abi.export_count,
        meaningful_exports: result.abi.meaningful_exports,
        prove_exports: result.abi.prove_exports,
        verify_exports: result.abi.verify_exports,
        challenge_exports: result.abi.challenge_exports,
        has_build_minimal_proof: result.abi.has_build_minimal_proof,
        wbindgen: result.abi.wbindgen,
        instantiate: result.instantiate,
      }
    : null;

  // Compile succeeded (eni6maValidate returns ok:true for probe path).
  const compileOk = !!result.abi;
  if (!compileOk) {
    return {
      ok: false,
      mode: "validate_failed",
      reason: result.reason || "wasm_compile_failed",
      validated: false,
    };
  }

  // Soft-instantiate preferred for DEV digest_only.
  const instOk = result.instantiate && result.instantiate.ok;

  if (gateStrict && !hasProof) {
    return {
      ok: false,
      mode: "proof_required",
      reason: "AGY_GATE_STRICT=1 requires proof or challenge_id",
      validated: false,
      abi: abiSummary,
    };
  }

  if (!hasProof) {
    if (gateDev) {
      // DEV: digest-only after successful instantiate (or compile if soft-inst fails on opaque ABI)
      if (instOk || result.abi.shape === "prove_only" || result.abi.shape === "wbindgen_opaque") {
        return {
          ok: true,
          mode: "digest_only",
          reason: instOk
            ? "proof_missing_dev_digest_only_instantiated"
            : "proof_missing_dev_digest_only_compile_ok",
          validated: false,
          warning: "digest_only",
          abi: abiSummary,
        };
      }
      return {
        ok: false,
        mode: "validate_failed",
        reason: `dev_instantiate_failed: ${(result.instantiate && result.instantiate.error) || "unknown"}`,
        validated: false,
        abi: abiSummary,
      };
    }
    if (failOpenGate) {
      return {
        ok: true,
        mode: "digest_ok",
        reason: "proof_missing_fail_open_digest_ok_abi_probe",
        validated: false,
        warning: "digest_ok",
        abi: abiSummary,
      };
    }
    return {
      ok: false,
      mode: "proof_required",
      reason: "proof_or_challenge_id_required",
      validated: false,
      abi: abiSummary,
    };
  }

  // Proof present but ABI opaque / prove-only: accept as abi_probe (not cryptographically verified).
  if (result.abi && (result.abi.verify_exports || []).length === 0) {
    if (gateStrict) {
      // Strict + proof present but no verify export: still require non-empty proof (already have it)
      // but mark as abi_probe not fully validated.
      return {
        ok: true,
        mode: "abi_probe",
        reason: result.reason || "abi_probe_no_verify_export",
        validated: false,
        warning: "abi_probe_unverified",
        abi: abiSummary,
      };
    }
    return {
      ok: true,
      mode: "abi_probe",
      reason: result.reason || "abi_probe",
      validated: false,
      warning: "abi_probe_unverified",
      abi: abiSummary,
    };
  }

  return {
    ok: true,
    mode: "eni6ma_verify_present",
    reason: result.reason,
    validated: !!result.wired,
    abi: abiSummary,
  };
}

/**
 * Extract circuit config from request body (compass.circuit or top-level circuit).
 */
function extractCircuit(body) {
  if (!body || typeof body !== "object") return null;
  if (body.compass && typeof body.compass === "object" && body.compass.circuit) {
    return body.compass.circuit;
  }
  if (body.circuit && typeof body.circuit === "object") return body.circuit;
  return null;
}

/**
 * Resolve circuit bytes: cache hit by sha256, url→sha index, or allowlisted fetch.
 * Fail closed on digest mismatch (HTTP 403 semantics via err.status).
 *
 * @returns {Promise<{ bytes, sha256, cached, source, gate }>}
 */
async function resolveCircuit(circuit) {
  if (!circuit || typeof circuit !== "object") {
    const err = new Error("circuit object required");
    err.code = "circuit_required";
    err.status = 400;
    throw err;
  }

  const dir = cacheDir();
  await ensureCacheDir(dir);

  const clientSha = normalizeClientSha(circuit.sha256 || circuit.digest || null);
  let normalizedUrl = null;
  if (circuit.url) {
    normalizedUrl = normalizeCircuitUrl(circuit.url);
  }

  // 1) Direct cache hit by client sha256
  if (clientSha) {
    const filePath = path.join(dir, clientSha);
    try {
      const bytes = await fsp.readFile(filePath);
      const actual = sha256Hex(bytes);
      if (actual !== clientSha) {
        try { await fsp.unlink(filePath); } catch (_) {}
      } else {
        return {
          bytes,
          sha256: actual,
          cached: true,
          source: "cache_sha256",
        };
      }
    } catch (e) {
      if (e.code !== "ENOENT") throw e;
    }
  }

  // 2) url→sha index
  if (normalizedUrl) {
    const index = await readUrlIndex(dir);
    const mapped = index[normalizedUrl];
    if (mapped && /^[a-f0-9]{64}$/.test(mapped)) {
      if (clientSha && clientSha !== mapped) {
        const err = new Error(
          `circuit.sha256 mismatch vs url-index (client=${clientSha} index=${mapped})`
        );
        err.code = "circuit_digest_mismatch";
        err.status = 403;
        throw err;
      }
      const filePath = path.join(dir, mapped);
      try {
        const bytes = await fsp.readFile(filePath);
        const actual = sha256Hex(bytes);
        if (actual === mapped && (!clientSha || clientSha === actual)) {
          return {
            bytes,
            sha256: actual,
            cached: true,
            source: "cache_url_index",
          };
        }
      } catch (e) {
        if (e.code !== "ENOENT") throw e;
      }
    }
  }

  // 3) Miss path — fetch
  if (!normalizedUrl) {
    const err = new Error("circuit.url required on cache miss");
    err.code = "circuit_url_required";
    err.status = 400;
    throw err;
  }

  const bytes = await fetchBytes(normalizedUrl);
  const actual = sha256Hex(bytes);

  const sidecarSha = await fetchSidecarSha(normalizedUrl);
  if (sidecarSha && sidecarSha !== actual) {
    const err = new Error(
      `circuit digest mismatch vs sidecar .sha256 (actual=${actual} sidecar=${sidecarSha})`
    );
    err.code = "circuit_digest_mismatch";
    err.status = 403;
    throw err;
  }
  if (clientSha && clientSha !== actual) {
    const err = new Error(
      `circuit digest mismatch vs client sha256 (actual=${actual} client=${clientSha})`
    );
    err.code = "circuit_digest_mismatch";
    err.status = 403;
    throw err;
  }

  // Write cache
  const outPath = path.join(dir, actual);
  const tmp = outPath + ".tmp";
  await fsp.writeFile(tmp, bytes);
  await fsp.rename(tmp, outPath);
  const index = await readUrlIndex(dir);
  index[normalizedUrl] = actual;
  await writeUrlIndex(dir, index);

  return {
    bytes,
    sha256: actual,
    cached: false,
    source: "fetch",
  };
}

/**
 * Full Gate: resolve + validate. Throws errors with .status for HTTP mapping.
 * Returns { ok, gate: { cached, sha256, source, validated, mode, abi? }, warning? }
 */
async function runCircuitGate(body) {
  const required = envTruthy("AGY_GATE_REQUIRED");

  const circuit = extractCircuit(body);
  if (!circuit) {
    if (required) {
      const err = new Error("compass.circuit (or circuit) is required");
      err.code = "circuit_required";
      err.status = 403;
      throw err;
    }
    return {
      ok: true,
      gate: {
        cached: false,
        sha256: null,
        source: "none",
        validated: false,
        mode: "no_circuit",
      },
    };
  }

  const resolved = await resolveCircuit(circuit);
  const v = await validateProof(resolved.bytes, circuit);
  if (!v.ok) {
    const err = new Error(`Gate/ENI6MA validate failed: ${v.reason || "denied"}`);
    err.code = "compass_gate_denied";
    err.status = 403;
    err.gate = {
      cached: resolved.cached,
      sha256: resolved.sha256,
      source: resolved.source,
      validated: false,
      mode: v.mode || "validate_failed",
    };
    if (v.abi) err.gate.abi = summarizeAbiForHttp(v.abi);
    throw err;
  }

  const gate = {
    cached: resolved.cached,
    sha256: resolved.sha256,
    source: resolved.source,
    validated: !!v.validated,
    mode: v.mode || "ok",
  };
  if (v.abi) gate.abi = summarizeAbiForHttp(v.abi);
  const out = { ok: true, gate };
  if (v.warning) out.warning = v.warning;
  return out;
}

/** Trim ABI for HTTP responses (avoid huge export dumps). */
function summarizeAbiForHttp(abi) {
  if (!abi) return null;
  return {
    shape: abi.shape,
    export_count: abi.export_count,
    meaningful_exports: abi.meaningful_exports,
    prove_exports: abi.prove_exports,
    verify_exports: abi.verify_exports,
    challenge_exports: abi.challenge_exports,
    has_build_minimal_proof: abi.has_build_minimal_proof,
    wbindgen: abi.wbindgen,
    instantiate: abi.instantiate
      ? { ok: abi.instantiate.ok, mode: abi.instantiate.mode }
      : undefined,
  };
}

module.exports = {
  ALLOWED_HOSTS,
  cacheDir,
  normalizeCircuitUrl,
  sha256Hex,
  extractCircuit,
  resolveCircuit,
  validateProof,
  eni6maValidate,
  probeAbi,
  runCircuitGate,
  parseSha256Sidecar,
  summarizeAbiForHttp,
};
