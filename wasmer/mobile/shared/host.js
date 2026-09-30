/* comPASS mobile host glue — same ABI as wasmer/browser/sandbox.js.
 * Loads compass_core_bg.wasm by SHA-256, sanitizes a keyless snapshot,
 * calls compass_decide_json, reports reason codes for Python parity.
 * No provider keys. Empty import table. Fail-open on trap.
 *
 * Works in: iOS WKWebView, Android WebView, Node (scripts/wasmer_mobile_glue_check.mjs).
 */
(function (global) {
  "use strict";

  var NOW_ISO = "2026-09-05T00:00:00Z";
  var FIXTURE_REQUEST = "implement a function";
  var MISSING_REQUEST = "x";
  var KEY_FIELD = /api[_-]?key|token|secret|authorization|password|credential/i;

  function hexFromBytes(u8) {
    var out = "";
    for (var i = 0; i < u8.length; i++) {
      var h = u8[i].toString(16);
      out += h.length === 1 ? "0" + h : h;
    }
    return out;
  }

  function sha256Hex(bytes) {
    var buf = bytes instanceof ArrayBuffer ? bytes : bytes.buffer;
    if (bytes instanceof Uint8Array) {
      buf = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    }
    if (global.crypto && global.crypto.subtle && typeof global.crypto.subtle.digest === "function") {
      return global.crypto.subtle.digest("SHA-256", buf).then(function (hash) {
        return hexFromBytes(new Uint8Array(hash));
      });
    }
    if (typeof process !== "undefined" && process.versions && process.versions.node) {
      return Promise.resolve().then(function () {
        var nodeCrypto = require("crypto");
        var u8 = bytes instanceof Uint8Array ? bytes : new Uint8Array(buf);
        return nodeCrypto.createHash("sha256").update(u8).digest("hex");
      });
    }
    return Promise.resolve(null);
  }

  function sanitizeValue(value) {
    if (Array.isArray(value)) {
      return value.map(sanitizeValue);
    }
    if (value && typeof value === "object") {
      var out = {};
      var keys = Object.keys(value);
      for (var i = 0; i < keys.length; i++) {
        var k = keys[i];
        if (KEY_FIELD.test(k)) continue;
        out[k] = sanitizeValue(value[k]);
      }
      return out;
    }
    return value;
  }

  function sanitizeSnapshotText(text) {
    if (text == null || text === "") return null;
    var parsed;
    try {
      parsed = typeof text === "string" ? JSON.parse(text) : text;
    } catch (e) {
      return typeof text === "string" ? text : JSON.stringify(text);
    }
    return JSON.stringify(sanitizeValue(parsed));
  }

  function writeUtf8(memory, alloc, text) {
    var bytes = new TextEncoder().encode(text);
    var ptr = alloc(bytes.length);
    new Uint8Array(memory.buffer, ptr, bytes.length).set(bytes);
    return { ptr: ptr, len: bytes.length };
  }

  function instantiateModule(wasmBytes) {
    return WebAssembly.instantiate(wasmBytes, {}).then(function (result) {
      var exp = result.instance.exports;
      if (!exp.compass_decide_json || !exp.compass_alloc || !exp.compass_last_len || !exp.memory) {
        throw new Error("missing compass_* exports");
      }
      var compiled = result.module || (wasmBytes instanceof WebAssembly.Module ? wasmBytes : null);
      var importPromise = compiled
        ? Promise.resolve(WebAssembly.Module.imports(compiled))
        : WebAssembly.compile(wasmBytes instanceof ArrayBuffer ? wasmBytes : wasmBytes.buffer || wasmBytes).then(function (mod) {
            return WebAssembly.Module.imports(mod);
          });
      return importPromise.then(function (imports) {
        for (var i = 0; i < imports.length; i++) {
          var im = imports[i];
          if (im.module === "keys" || im.name === "fetch" || String(im.name).indexOf("fetch") !== -1) {
            throw new Error("forbidden import: " + im.module + "." + im.name);
          }
        }
        return {
          memory: exp.memory,
          alloc: exp.compass_alloc,
          free: exp.compass_free,
          decide: exp.compass_decide_json,
          lastLen: exp.compass_last_len,
        };
      });
    });
  }

  function decide(api, request, snapshotText, nowIso) {
    try {
      var r = writeUtf8(api.memory, api.alloc, request || "");
      var s = snapshotText == null
        ? { ptr: 0, len: 0 }
        : writeUtf8(api.memory, api.alloc, snapshotText);
      var n = writeUtf8(api.memory, api.alloc, nowIso || NOW_ISO);
      var outPtr = api.decide(r.ptr, r.len, s.ptr, s.len, n.ptr, n.len);
      var outLen = api.lastLen();
      var jsonBytes = new Uint8Array(api.memory.buffer, outPtr, outLen);
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

  function b64ToBytes(b64) {
    var bin = global.atob(b64);
    var u8 = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return u8;
  }

  function runFromBytes(wasmBytes, opts) {
    opts = opts || {};
    var expected = String(opts.expectedSha256 || "").trim().toLowerCase();
    var snapshotJson = opts.snapshotJson;
    var nowIso = opts.nowIso || NOW_ISO;
    var bytes = wasmBytes instanceof Uint8Array ? wasmBytes : new Uint8Array(wasmBytes);
    var report = {
      ok: false,
      expected_sha256: expected,
      actual_sha256: opts.nativeActualSha256 || null,
      digest_match: false,
      js_digest: null,
      import_table: "pending",
      fixture_min: null,
      missing: null,
      error: null,
    };

    return sha256Hex(bytes)
      .then(function (got) {
        report.js_digest = got == null ? "skipped_no_subtle" : "sha-256";
        if (got) report.actual_sha256 = got;
        if (got) {
          report.digest_match = got.toLowerCase() === expected;
          if (!report.digest_match) {
            report.error = "digest mismatch: expected " + expected + " got " + got;
            return report;
          }
        } else if (opts.requireJsDigest) {
          report.error = "js digest unavailable and requireJsDigest=true";
          return report;
        } else {
          report.digest_match = opts.nativeDigestMatch === true;
          if (opts.nativeDigestMatch === false) {
            report.error = "native digest mismatch; refusing instantiate";
            return report;
          }
        }
        return instantiateModule(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)).then(function (api) {
          report.import_table = "empty";
          var sanitized = sanitizeSnapshotText(snapshotJson);
          report.fixture_min = decide(api, FIXTURE_REQUEST, sanitized, nowIso);
          report.missing = decide(api, MISSING_REQUEST, null, nowIso);
          var cheap = report.fixture_min && report.fixture_min.selected_model_version_id === "urn:mg:model:cheap";
          var miss = report.missing && report.missing.default_reason === "snapshot_missing";
          report.ok = !!(cheap && miss && (report.digest_match || report.js_digest === "skipped_no_subtle"));
          if (!cheap) report.error = (report.error || "") + " fixture_min did not select urn:mg:model:cheap";
          if (!miss) report.error = (report.error || "") + " missing snapshot did not return snapshot_missing";
          return report;
        });
      })
      .catch(function (e) {
        report.error = String(e && e.stack ? e.stack : e);
        report.ok = false;
        return report;
      });
  }

  function reportToHost(payload) {
    var json = typeof payload === "string" ? payload : JSON.stringify(payload);
    try {
      if (global.webkit && global.webkit.messageHandlers && global.webkit.messageHandlers.compassResult) {
        global.webkit.messageHandlers.compassResult.postMessage(payload);
      }
    } catch (e1) { /* ignore */ }
    try {
      if (global.CompassNative && typeof global.CompassNative.report === "function") {
        global.CompassNative.report(json);
      }
    } catch (e2) { /* ignore */ }
    if (typeof document !== "undefined") {
      var el = document.getElementById("out");
      if (el) el.textContent = JSON.stringify(payload, null, 2);
      document.documentElement.setAttribute("data-compass-ok", payload && payload.ok ? "1" : "0");
    }
    return payload;
  }

  function bootInjected() {
    var inj = global.__COMPASS_INJECT;
    if (!inj || !inj.wasmB64) return Promise.reject(new Error("no __COMPASS_INJECT.wasmB64"));
    var bytes = b64ToBytes(inj.wasmB64);
    return runFromBytes(bytes, {
      expectedSha256: inj.expectedSha256,
      snapshotJson: inj.snapshotJson,
      nowIso: inj.nowIso || NOW_ISO,
      nativeDigestMatch: inj.nativeDigestMatch,
      nativeActualSha256: inj.nativeActualSha256,
      requireJsDigest: false,
    }).then(reportToHost);
  }

  function fetchText(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("fetch failed " + res.status + " " + url);
      return res.text();
    });
  }

  function bootFetched() {
    return Promise.all([
      fetch("EXPECTED_SHA256").then(function (res) {
        if (!res.ok) throw new Error("EXPECTED_SHA256 fetch " + res.status);
        return res.text();
      }),
      fetch("compass_core_bg.wasm").then(function (res) {
        if (!res.ok) throw new Error("wasm fetch " + res.status);
        return res.arrayBuffer();
      }),
      fetchText("snapshot_min.json"),
    ]).then(function (parts) {
      var expected = String(parts[0]).trim();
      var wasm = parts[1];
      var snapshot = parts[2];
      return runFromBytes(new Uint8Array(wasm), {
        expectedSha256: expected,
        snapshotJson: snapshot,
        nowIso: NOW_ISO,
        requireJsDigest: false,
      });
    }).then(reportToHost);
  }

  function bootAuto() {
    if (global.__COMPASS_INJECT && global.__COMPASS_INJECT.wasmB64) return bootInjected();
    if (typeof fetch === "function") return bootFetched();
    return Promise.reject(new Error("no inject payload and no fetch"));
  }

  var api = {
    NOW_ISO: NOW_ISO,
    sanitizeSnapshotText: sanitizeSnapshotText,
    runFromBytes: runFromBytes,
    bootInjected: bootInjected,
    bootFetched: bootFetched,
    bootAuto: bootAuto,
    reportToHost: reportToHost,
  };
  global.CompassMobileHost = api;

  if (typeof document !== "undefined" && !global.__COMPASS_NO_AUTOBOOT) {
    var start = function () {
      bootAuto().catch(function (e) {
        reportToHost({ ok: false, error: String(e) });
      });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
