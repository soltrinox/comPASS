/**
 * ENI6MA circuit Gate for agy-bridge.
 *
 * Resolve / pin / cache WASM circuits, fail-closed on digest mismatch,
 * then stub-validate proof (replaceable with real ENI6MA ABI later).
 *
 * See docs/adr/0007-agy-behind-eni6ma-gate.md and README.md.
 */

"use strict";

const crypto = require("crypto");
const fs = require("fs");
const fsp = require("fs").promises;
const os = require("os");
const path = require("path");
const { URL } = require("url");

const ALLOWED_HOSTS = new Set(["raw.githubusercontent.com", "github.com"]);

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
    // /owner/repo/blob/ref/path... → raw.githubusercontent.com/owner/repo/ref/path...
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
  // "hex" or "hex  filename" or "hex *filename"
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

/**
 * Stub ENI6MA validate — real ABI can replace this later.
 * For now: proof must be non-empty object/string AND wasm must instantiate.
 */
async function eni6maValidate(wasmBytes, proof, challengeId) {
  const proofOk =
    (typeof proof === "string" && proof.trim().length > 0) ||
    (proof && typeof proof === "object" && !Array.isArray(proof) && Object.keys(proof).length > 0) ||
    (typeof challengeId === "string" && challengeId.trim().length > 0);

  if (!proofOk) {
    return { ok: false, reason: "proof_or_challenge_empty" };
  }

  try {
    const mod = await WebAssembly.compile(wasmBytes);
    try {
      await WebAssembly.instantiate(mod, {});
    } catch (instErr) {
      // Many circuits need imports; compile success is enough for stub load-OK.
      // Still require compile to succeed.
      if (!mod) throw instErr;
    }
    return { ok: true, reason: "stub_eni6ma_ok" };
  } catch (e) {
    return {
      ok: false,
      reason: `wasm_instantiate_failed: ${e && e.message ? e.message : e}`,
    };
  }
}

async function validateProof(wasmBytes, circuit) {
  const proof = circuit && circuit.proof;
  const challengeId = circuit && (circuit.challenge_id || circuit.challengeId);
  const hasProof =
    (typeof proof === "string" && proof.trim()) ||
    (proof && typeof proof === "object" && Object.keys(proof).length > 0) ||
    (typeof challengeId === "string" && challengeId.trim());

  const gateDev =
    String(process.env.AGY_GATE_DEV || "").toLowerCase() === "1" ||
    String(process.env.AGY_GATE_DEV || "").toLowerCase() === "true" ||
    String(process.env.AGY_GATE_DEV || "").toLowerCase() === "yes";
  // "AGY_FAIL_OPEN gate mode" — treat truthy AGY_FAIL_OPEN as digest_only when no proof
  const failOpenGate =
    String(process.env.AGY_FAIL_OPEN || "1").toLowerCase() !== "0" &&
    String(process.env.AGY_FAIL_OPEN || "1").toLowerCase() !== "false";

  // Always try compile for load OK
  let compileOk = false;
  let compileErr = null;
  try {
    const mod = await WebAssembly.compile(wasmBytes);
    compileOk = !!mod;
    try {
      await WebAssembly.instantiate(mod, {});
    } catch (_) {
      /* imports may be required; compile is enough */
    }
  } catch (e) {
    compileErr = e && e.message ? e.message : String(e);
  }

  if (!compileOk) {
    return {
      ok: false,
      mode: "validate_failed",
      reason: `wasm_compile_failed: ${compileErr || "unknown"}`,
      validated: false,
    };
  }

  if (!hasProof) {
    if (gateDev || failOpenGate) {
      return {
        ok: true,
        mode: "digest_only",
        reason: "proof_missing_dev_digest_only",
        validated: false,
        warning: "digest_only",
      };
    }
    return {
      ok: false,
      mode: "validate_failed",
      reason: "proof_or_challenge_id_required",
      validated: false,
    };
  }

  const stub = await eni6maValidate(wasmBytes, proof, challengeId);
  if (!stub.ok) {
    return {
      ok: false,
      mode: "validate_failed",
      reason: stub.reason || "eni6ma_validate_failed",
      validated: false,
    };
  }
  return {
    ok: true,
    mode: "stub_eni6ma",
    reason: stub.reason,
    validated: true,
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
        // Corrupt cache entry — remove and fall through
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
 * Returns { ok, gate: { cached, sha256, source, validated, mode }, warning? }
 */
async function runCircuitGate(body) {
  const required =
    String(process.env.AGY_GATE_REQUIRED || "").toLowerCase() === "1" ||
    String(process.env.AGY_GATE_REQUIRED || "").toLowerCase() === "true";

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
    throw err;
  }

  const gate = {
    cached: resolved.cached,
    sha256: resolved.sha256,
    source: resolved.source,
    validated: !!v.validated,
    mode: v.mode || "ok",
  };
  const out = { ok: true, gate };
  if (v.warning) out.warning = v.warning;
  return out;
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
  runCircuitGate,
  parseSha256Sidecar,
};
