/* Path-B circuit loader: fetch bytes, SHA-256, fail closed on pin mismatch. */
(function (root) {
  async function sha256Hex(buf) {
    const dig = await crypto.subtle.digest("SHA-256", buf);
    return [...new Uint8Array(dig)]
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  /**
   * @param {string} url - untrusted hint (same-origin path preferred)
   * @param {string} expectedSha256 - authority pin (required)
   * @returns {Promise<{bytes: ArrayBuffer, sha256: string, url: string}>}
   */
  async function loadPinned(url, expectedSha256) {
    const expected = String(expectedSha256 || "")
      .trim()
      .split(/\s+/)[0]
      .toLowerCase();
    if (!/^[0-9a-f]{64}$/.test(expected)) {
      const err = new Error("circuitLoader: missing or invalid authority pin");
      err.code = "pin_invalid";
      throw err;
    }
    const res = await fetch(url);
    if (!res.ok) {
      const err = new Error("circuitLoader: fetch failed " + res.status);
      err.code = "fetch_failed";
      throw err;
    }
    const bytes = await res.arrayBuffer();
    const actual = await sha256Hex(bytes);
    if (actual !== expected) {
      const err = new Error("circuitLoader: DIGEST MISMATCH — fail closed");
      err.code = "digest_mismatch";
      err.expected = expected;
      err.actual = actual;
      err.bytes = bytes.byteLength;
      throw err;
    }
    return { bytes: bytes, sha256: actual, url: url };
  }

  /**
   * Load pins.json then a named pin. Paths in pins are relative to wasmer/.
   * From wasmer/browser/, resolve as ../<path>.
   */
  async function loadPinnedById(pinsUrl, pinId) {
    const pinsRes = await fetch(pinsUrl);
    if (!pinsRes.ok) throw new Error("circuitLoader: pins fetch " + pinsRes.status);
    const pinsDoc = await pinsRes.json();
    const pin = pinsDoc && pinsDoc.pins && pinsDoc.pins[pinId];
    if (!pin || !pin.sha256) {
      const err = new Error("circuitLoader: unknown pin id " + pinId);
      err.code = "pin_missing";
      throw err;
    }
    const url = new URL("../" + pin.path, location.href).href;
    const loaded = await loadPinned(url, pin.sha256);
    return Object.assign({ pinId: pinId, pin: pin, pinsDoc: pinsDoc }, loaded);
  }

  const api = {
    sha256Hex: sha256Hex,
    loadPinned: loadPinned,
    loadPinnedById: loadPinnedById,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CircuitLoader = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
