/* Zone A: @wasmer/sdk/browser boot + local compass guest.
 * Dynamic import of the /browser entrypoint (static import is documented
 * to crash workers). Guard sandbox creation on crossOriginIsolated.
 * compass/decide is NOT fetched from the registry (publish NOT_RUN).
 */
const statusEl = document.getElementById("status");
const outEl = document.getElementById("out");
const NOW = "2026-09-05T00:00:00Z";
const REQUEST = "implement a function";

let pins = {
  registry_packages: { python: "python/python@=3.13.18" },
};

const report = {
  isolated: window.crossOriginIsolated === true,
  sdk: { imported: false, ready: false, error: null },
  compass_host: { grade: "NOT_RUN", decision: null, error: null },
  compass_webc: { grade: "NOT_RUN", decision: null, error: null, note: null },
  python: { grade: "NOT_RUN", pin: "python/python@=3.13.18", output: null, error: null },
  registry_compass: { attempted: false, note: "NOT_RUN — wasmer/PUBLISH-NOT_RUN.md; no fake registry fetch" },
};

function setStatus(msg, ok) {
  statusEl.textContent = msg;
  statusEl.className = ok === true ? "ok" : ok === false ? "err" : "";
  document.documentElement.dataset.zoneaStatus = msg;
}

function publish() {
  document.documentElement.dataset.zoneaIsolated = report.isolated ? "1" : "0";
  document.documentElement.dataset.zoneaSdk = report.sdk.ready ? "1" : "0";
  document.documentElement.dataset.zoneaHost = report.compass_host.grade;
  document.documentElement.dataset.zoneaWebc = report.compass_webc.grade;
  document.documentElement.dataset.zoneaPython = report.python.grade;
  document.documentElement.dataset.zoneaOut = JSON.stringify(report);
  outEl.textContent = JSON.stringify(report, null, 2);
}

function writeUtf8(memory, alloc, text) {
  const bytes = new TextEncoder().encode(text);
  const ptr = alloc(bytes.length);
  new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
  return { ptr, len: bytes.length };
}

function decideWithExports(exp, request, snapshotText, nowIso) {
  try {
    const r = writeUtf8(exp.memory, exp.compass_alloc, request);
    const s = snapshotText == null
      ? { ptr: 0, len: 0 }
      : writeUtf8(exp.memory, exp.compass_alloc, snapshotText);
    const n = writeUtf8(exp.memory, exp.compass_alloc, nowIso || NOW);
    const outPtr = exp.compass_decide_json(r.ptr, r.len, s.ptr, s.len, n.ptr, n.len);
    const outLen = exp.compass_last_len();
    const jsonBytes = new Uint8Array(exp.memory.buffer, outPtr, outLen);
    return JSON.parse(new TextDecoder().decode(jsonBytes));
  } catch (e) {
    return {
      fail_open: true,
      default_reason: "module_trap",
      selected_model_version_id: "default",
      rationale: "fail-open: module_trap",
      error: String(e),
    };
  }
}

function parityOk(d) {
  return Boolean(
    d &&
      d.fail_open === false &&
      d.selected_model_version_id === "urn:mg:model:cheap" &&
      (d.default_reason === null || d.default_reason === undefined)
  );
}

async function hostInstantiateCompass(snapshotText) {
  const wasmUrl = new URL("../artifacts/compass_core_bg.wasm", import.meta.url);
  const res = await fetch(wasmUrl);
  if (!res.ok) throw new Error("wasm fetch failed: " + res.status);
  const bytes = await res.arrayBuffer();
  const { instance } = await WebAssembly.instantiate(bytes, {});
  const exp = instance.exports;
  if (!exp.compass_decide_json || !exp.compass_alloc || !exp.compass_last_len || !exp.memory) {
    throw new Error("missing compass_* exports");
  }
  const fixture = decideWithExports(exp, REQUEST, snapshotText, NOW);
  const missing = decideWithExports(exp, "x", null, NOW);
  const corrupt = decideWithExports(exp, "x", "{truncated", NOW);
  const missingOk = missing && missing.fail_open === true && missing.default_reason === "snapshot_missing";
  const corruptOk = corrupt && corrupt.fail_open === true && corrupt.default_reason === "snapshot_corrupt";
  report.compass_host = {
    grade: parityOk(fixture) && missingOk && corruptOk ? "FULL" : "PARTIAL",
    source: wasmUrl.pathname,
    decision: fixture,
    missing_reason: missing && missing.default_reason,
    corrupt_reason: corrupt && corrupt.default_reason,
    error: null,
  };
}

async function loadLocalWebc() {
  const url = new URL("../artifacts/compass-decide-0.1.0.webc", import.meta.url);
  const res = await fetch(url);
  if (!res.ok) {
    return { ok: false, status: res.status, url: url.pathname };
  }
  return { ok: true, bytes: new Uint8Array(await res.arrayBuffer()), url: url.pathname };
}

function lastJsonLine(text) {
  const lines = String(text || "").trim().split(/\r?\n/).filter(Boolean);
  if (!lines.length) return null;
  return JSON.parse(lines[lines.length - 1]);
}

function withTimeout(promise, ms, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(label + " timed out after " + ms + "ms")), ms);
    }),
  ]);
}

async function bootSdkAndGuests(snapshotText) {
  if (!report.isolated) {
    report.sdk.error = "not_cross_origin_isolated";
    report.compass_webc.note = "SDK sandbox skipped: page is not cross-origin isolated; host instantiate remains the fail-open path";
    report.python.grade = "NOT_RUN";
    report.python.error = "not_cross_origin_isolated";
    return;
  }

  let Wasmer;
  try {
    // Dynamic import of the /browser entrypoint. A static import is documented
    // to pull DOM-touching dependencies into workers and crash them.
    // Dynamic import of the package "./browser" entry (dist/index.js).
    // Bare "@wasmer/sdk/browser" needs an import map, and import maps are
    // inline scripts that CSP would have to hash or allow via unsafe-inline.
    // Same file the package exports as "./browser".
    const mod = await import(
      new URL("./vendor/@wasmer/sdk/dist/index.js", import.meta.url).href
    );
    Wasmer = mod.Wasmer;
    report.sdk.imported = true;
  } catch (e) {
    report.sdk.error = String(e);
    report.compass_webc.grade = "NOT_RUN";
    report.compass_webc.error = "sdk_import_failed";
    report.python.grade = "NOT_RUN";
    report.python.error = "sdk_import_failed";
    return;
  }

  let wasmer;
  try {
    wasmer = new Wasmer();
    await wasmer.ready();
    report.sdk.ready = true;
  } catch (e) {
    report.sdk.error = String(e);
    report.python.grade = "NOT_RUN";
    report.python.error = "sdk_ready_failed";
    report.compass_webc.grade = "NOT_RUN";
    report.compass_webc.error = String(e);
    return;
  }

  const webc = await loadLocalWebc();
  if (!webc.ok) {
    report.compass_webc = {
      grade: "NOT_RUN",
      decision: null,
      error: "local_webc_http_" + webc.status,
      note: "Local .webc not served (gitignored build artifact). Host compass_decide_json path is the compass guest.",
    };
  } else {
    try {
      const sandbox = await withTimeout(
        wasmer.sandboxes.create({ packages: [webc.bytes] }),
        60000,
        "local_webc_sandbox"
      );
      const output = await withTimeout(
        sandbox.command("compass-decide", [
          "--request",
          REQUEST,
          "--snapshot",
          "/wasmer/fixtures/snapshot_min.json",
          "--now",
          NOW,
        ]).run(),
        60000,
        "local_webc_compass_decide"
      );
      const decision = lastJsonLine(output.text());
      report.compass_webc = {
        grade: parityOk(decision) ? "FULL" : "PARTIAL",
        source: "local_webc",
        bytes: webc.bytes.byteLength,
        decision,
        stdout_ok: output.ok,
        error: null,
      };
      await sandbox.close();
    } catch (e) {
      report.compass_webc = {
        grade: "PARTIAL",
        decision: null,
        error: String(e),
        note: "Local webc loaded but sandbox/command failed",
      };
    }
  }

  const skipPython = new URLSearchParams(location.search).get("python") === "0";
  if (skipPython) {
    report.python.grade = "NOT_RUN";
    report.python.error = "skipped_by_query";
    report.python.note = "Pass ?python=0 to skip the ~157MB python/python download";
  } else {
    try {
      const sandbox = await withTimeout(
        wasmer.sandboxes.create({
          packages: [pins.registry_packages.python],
        }),
        180000,
        "python_sandbox"
      );
      const output = await withTimeout(
        sandbox.command("python", ["-c", "print('zone-a-python-ok')"]).run(),
        60000,
        "python_print"
      );
      const text = output.text().trim();
      report.python = {
        grade: output.ok && text.includes("zone-a-python-ok") ? "FULL" : "PARTIAL",
        pin: pins.registry_packages.python,
        output: text,
        error: null,
        source: "registry",
      };
      await sandbox.close();
    } catch (e) {
      report.python = {
        grade: "NOT_RUN",
        pin: pins.registry_packages.python,
        output: null,
        error: String(e),
        note: "Honest NOT_RUN: registry python/python download did not complete (auth, COEP/CORP, network, or size). Compass guest does not depend on this.",
      };
    }
  }

  try {
    await wasmer.close();
  } catch {
    /* ignore */
  }
}

async function boot() {
  setStatus("loading…");
  publish();
  try {
    pins = await (await fetch(new URL("./sdk-pins.json", import.meta.url))).json();
    report.python.pin = pins.registry_packages.python;
  } catch (e) {
    report.sdk.error = "sdk-pins.json: " + String(e);
  }
  let snapshotText = "";
  try {
    const snapUrl = new URL("../fixtures/snapshot_min.json", import.meta.url);
    const res = await fetch(snapUrl);
    if (!res.ok) throw new Error("snapshot fetch failed: " + res.status);
    snapshotText = await res.text();
  } catch (e) {
    report.compass_host = { grade: "NOT_RUN", decision: null, error: String(e) };
    document.documentElement.dataset.zoneaReady = "0";
    document.documentElement.dataset.zoneaDone = "1";
    document.documentElement.dataset.zoneaError = String(e);
    setStatus("snapshot load failed", false);
    publish();
    return;
  }

  try {
    await hostInstantiateCompass(snapshotText);
  } catch (e) {
    report.compass_host = { grade: "NOT_RUN", decision: null, error: String(e) };
  }

  try {
    await bootSdkAndGuests(snapshotText);
  } catch (e) {
    report.sdk.error = String(e);
  }

  const hostOk = report.compass_host.grade === "FULL";
  const sdkOk = report.sdk.ready;
  setStatus(
    "isolated=" + report.isolated + " sdk=" + sdkOk + " host=" + report.compass_host.grade,
    hostOk
  );
  document.documentElement.dataset.zoneaReady = hostOk ? "1" : "0";
  document.documentElement.dataset.zoneaDone = "1";
  publish();
}

window.__COMPASS_ZONEA__ = {
  report: () => report,
  pins,
};

boot().catch((e) => {
  document.documentElement.dataset.zoneaReady = "0";
  document.documentElement.dataset.zoneaDone = "1";
  document.documentElement.dataset.zoneaError = String(e);
  setStatus("boot failed: " + e, false);
  publish();
});
