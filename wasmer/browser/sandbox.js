/* comPASS browser sandbox — host glue for compass_core_bg.wasm (Track D).
 * No provider keys. No fetch import on the module. Fail-open on trap.
 */
(() => {
  const FIXTURE = {
    schema: "model-graph/v1",
    nodes: [
      {
        id: "urn:mg:model:cheap",
        kind: "ModelVersion",
        status: "active",
        valid_start: "2026-01-01T00:00:00Z",
        valid_end: null,
        attrs: { quality: 0.7, cost: 0.1 },
      },
      {
        id: "urn:mg:model:pricey",
        kind: "ModelVersion",
        status: "active",
        valid_start: "2026-01-01T00:00:00Z",
        valid_end: null,
        attrs: { quality: 0.75, cost: 0.5 },
      },
    ],
    edges: [],
  };

  const statusEl = document.getElementById("status");
  const outEl = document.getElementById("out");
  let api = null;

  function setStatus(msg, ok) {
    statusEl.textContent = msg;
    statusEl.className = ok === true ? "ok" : ok === false ? "err" : "";
  }

  function writeUtf8(memory, alloc, text) {
    const bytes = new TextEncoder().encode(text);
    const ptr = alloc(bytes.length);
    new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
    return { ptr, len: bytes.length };
  }

  async function loadModule() {
    // Same-origin relative path — CSP connect-src 'self' only.
    const res = await fetch("../artifacts/compass_core_bg.wasm");
    if (!res.ok) throw new Error("wasm fetch failed: " + res.status);
    const bytes = await res.arrayBuffer();
    // Instantiation imports: none (no fetch host import for browser build).
    const { instance } = await WebAssembly.instantiate(bytes, {});
    const exp = instance.exports;
    if (!exp.compass_decide_json || !exp.compass_alloc || !exp.compass_last_len || !exp.memory) {
      throw new Error("missing compass_* exports");
    }
    // Guard: no keys.* / fetch imports on the module
    const imports = WebAssembly.Module.imports(
      (await WebAssembly.compile(bytes))
    );
    for (const im of imports) {
      if (im.module === "keys" || im.name === "fetch" || String(im.name).includes("fetch")) {
        throw new Error("forbidden import: " + im.module + "." + im.name);
      }
    }
    api = {
      memory: exp.memory,
      alloc: exp.compass_alloc,
      free: exp.compass_free,
      decide: exp.compass_decide_json,
      lastLen: exp.compass_last_len,
    };
    setStatus("module loaded (no fetch import)", true);
  }

  function decide(request, snapshotText, nowIso) {
    if (!api) throw new Error("module not loaded");
    try {
      const r = writeUtf8(api.memory, api.alloc, request);
      const s = snapshotText == null
        ? { ptr: 0, len: 0 }
        : writeUtf8(api.memory, api.alloc, snapshotText);
      const n = writeUtf8(api.memory, api.alloc, nowIso || "2026-09-05T00:00:00Z");
      const outPtr = api.decide(r.ptr, r.len, s.ptr, s.len, n.ptr, n.len);
      const outLen = api.lastLen();
      const jsonBytes = new Uint8Array(api.memory.buffer, outPtr, outLen);
      const text = new TextDecoder().decode(jsonBytes);
      return JSON.parse(text);
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

  async function boot() {
    try {
      await loadModule();
    } catch (e) {
      setStatus("load failed: " + e, false);
      outEl.textContent = String(e);
    }
  }

  document.getElementById("run").onclick = () => {
    const d = decide("implement a function", JSON.stringify(FIXTURE), "2026-09-05T00:00:00Z");
    outEl.textContent = JSON.stringify(d, null, 2);
    setStatus(d.fail_open ? "fail-open" : "ok: " + d.selected_model_version_id, !d.fail_open);
  };
  document.getElementById("missing").onclick = () => {
    const d = decide("x", null, "2026-09-05T00:00:00Z");
    outEl.textContent = JSON.stringify(d, null, 2);
    setStatus(d.default_reason || "?", d.default_reason === "snapshot_missing");
  };
  document.getElementById("corrupt").onclick = () => {
    const d = decide("x", "{truncated", "2026-09-05T00:00:00Z");
    outEl.textContent = JSON.stringify(d, null, 2);
    setStatus(d.default_reason || "?", d.default_reason === "snapshot_corrupt");
  };

  boot();
})();
