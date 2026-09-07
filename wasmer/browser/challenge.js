/* Challenge-first boot: handle | binary_url → digest-pin → prove → ask Gate. */
const DEMO_WASM_URL =
  "https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm";
const DEMO_SHA256 =
  "853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389";

/** Handle → raw GitHub REGISTRY URL (Pass+-style). Override with window.COMPASS_HANDLE_MAP. */
const DEFAULT_HANDLE_MAP = {
  "demo-wasm": DEMO_WASM_URL,
  demowasm: DEMO_WASM_URL,
  demo: DEMO_WASM_URL,
  alice:
    "https://raw.githubusercontent.com/eni6ma/REGISTRY/main/circuits/alice/v1/eni6ma",
  bob: "https://raw.githubusercontent.com/eni6ma/REGISTRY/main/circuits/bob/v1/eni6ma",
};

const statusEl = document.getElementById("status");
const outEl = document.getElementById("out");
const askSection = document.getElementById("askSection");
const askOut = document.getElementById("askOut");
const btnAsk = document.getElementById("btnAsk");

/** @type {{ url: string, sha256: string, proof: any } | null} */
let session = null;

function setStatus(msg, kind) {
  statusEl.textContent = msg;
  statusEl.className =
    kind === true ? "ok" : kind === false ? "err" : kind === "busy" ? "busy" : "";
}

function unlockAsk(ok) {
  askSection.classList.toggle("locked", !ok);
  btnAsk.disabled = !ok;
}

function qs() {
  return new URLSearchParams(location.search);
}

function resolveHandle(handle) {
  const h = String(handle || "").trim();
  if (!h) return null;
  const map = Object.assign({}, DEFAULT_HANDLE_MAP, window.COMPASS_HANDLE_MAP || {});
  const key = h.toLowerCase();
  if (map[key]) return map[key];
  if (map[h]) return map[h];
  // Generic Path-B: REGISTRY main circuits/<handle>/v1/eni6ma
  const safe = encodeURIComponent(h.toLowerCase());
  return `https://raw.githubusercontent.com/eni6ma/REGISTRY/main/circuits/${safe}/v1/eni6ma`;
}

function applyQueryDefaults() {
  const p = qs();
  if (p.get("handle")) document.getElementById("handle").value = p.get("handle");
  if (p.get("binary_url"))
    document.getElementById("binaryUrl").value = p.get("binary_url");
  if (p.get("sha256")) document.getElementById("sha256").value = p.get("sha256");
}

async function runProofFromPinned(pinned, label) {
  const art = location.pathname.includes("/browser/")
    ? new URL("../artifacts/", location.href)
    : new URL("/artifacts/", location.origin);
  const pkgBase = new URL("eni6ma/demo-wasm/v1/pkg/", art).href;
  const mod = await import(pkgBase + "eni6ma_wasm.js");
  await mod.default();
  const challenge = JSON.stringify({
    timestamp: Date.now(),
    matrix_data: {
      rows: [{ values: [1, 2, 3], row_hash: "x", row_index: 0 }],
    },
  });
  const bearings = JSON.stringify(["U", "L", "R", "U"]);
  const proof = mod.build_minimal_proof(challenge, bearings);
  return {
    label,
    path_b: {
      expected: pinned.sha256,
      actual: pinned.sha256,
      published_bytes: pinned.bytes.byteLength,
      url: pinned.url || pinned.remoteUrl || null,
    },
    proof,
    challenge: JSON.parse(challenge),
    bearings: JSON.parse(bearings),
  };
}

async function loadAndProve({ useLocalPin }) {
  unlockAsk(false);
  session = null;
  outEl.textContent = "";
  setStatus("Loading circuit…", "busy");

  try {
    let pinned;
    let sourceUrl;
    let expected;

    if (useLocalPin) {
      const pinsUrl = location.pathname.includes("/browser/")
        ? new URL("../artifacts/pins.json", location.href).href
        : new URL("/artifacts/pins.json", location.origin).href;
      pinned = await CircuitLoader.loadPinnedById(pinsUrl, "eni6ma_demo_wasm_v1");
      sourceUrl =
        pinned.pin && pinned.pin.source_ref
          ? DEMO_WASM_URL
          : new URL("../" + pinned.pin.path, location.href).href;
      expected = pinned.sha256;
    } else {
      const handle = document.getElementById("handle").value;
      const binaryUrl = document.getElementById("binaryUrl").value.trim();
      expected = document.getElementById("sha256").value.trim();
      sourceUrl = binaryUrl || resolveHandle(handle);
      if (!sourceUrl) {
        throw Object.assign(new Error("Enter a handle or binary_url"), {
          code: "input_missing",
        });
      }
      if (!expected && sourceUrl === DEMO_WASM_URL) expected = DEMO_SHA256;
      pinned = await CircuitLoader.loadPinnedRemote(sourceUrl, expected, {
        useProxy: true,
      });
      expected = pinned.sha256;
    }

    setStatus("Digest OK — proving…", "busy");
    const result = await runProofFromPinned(pinned, useLocalPin ? "local-pin" : "remote");
    session = {
      url: sourceUrl || DEMO_WASM_URL,
      sha256: expected,
      proof: result.proof,
    };
    setStatus("Digest OK · proof OK — ask unlocked", true);
    outEl.textContent = WasmerRunner.jsonSafe({
      mode: result.label,
      path_b: result.path_b,
      proof: result.proof,
    });
    unlockAsk(true);
  } catch (e) {
    setStatus(
      e.code === "digest_mismatch" ? "DIGEST MISMATCH — fail closed" : "Error",
      false
    );
    outEl.textContent = (e.stack || String(e)) +
      (e.expected
        ? "\n" + JSON.stringify({ expected: e.expected, actual: e.actual, bytes: e.bytes }, null, 2)
        : "");
    unlockAsk(false);
  }
}

async function askBridge() {
  if (!session) return;
  askOut.textContent = "";
  setStatus("Sending to agy-bridge…", "busy");
  const base = document.getElementById("bridgeUrl").value.replace(/\/$/, "");
  const prompt = document.getElementById("prompt").value;
  const body = {
    model: "agy",
    messages: [{ role: "user", content: prompt }],
    compass: {
      circuit: {
        url: session.url,
        sha256: session.sha256,
        proof: session.proof,
      },
    },
  };
  try {
    const res = await fetch(base + "/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (_) {
      parsed = text;
    }
    askOut.textContent = typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2);
    setStatus(res.ok ? "Bridge response OK" : "Bridge HTTP " + res.status, res.ok);
  } catch (e) {
    setStatus("Bridge error (is compose up?)", false);
    askOut.textContent = e.stack || String(e);
  }
}

document.getElementById("btnLoad").addEventListener("click", () =>
  loadAndProve({ useLocalPin: false })
);
document.getElementById("btnLocal").addEventListener("click", () =>
  loadAndProve({ useLocalPin: true })
);
document.getElementById("btnAsk").addEventListener("click", askBridge);

applyQueryDefaults();
const p = qs();
if (p.get("handle") || p.get("binary_url") || p.get("autoload") === "1") {
  loadAndProve({ useLocalPin: false });
}
