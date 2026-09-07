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
    // pin.path is relative to wasmer/ (e.g. artifacts/...). Resolve from pins.json URL parent/parent or /artifacts sibling.
    let url;
    try {
      const pinsBase = new URL(pinsUrl, location.href);
      // pins at .../artifacts/pins.json → artifact root is dirname
      const artRoot = new URL("./", pinsBase);
      const rel = String(pin.path).replace(/^artifacts\//, "");
      url = new URL(rel, artRoot).href;
    } catch (_) {
      url = new URL("../" + pin.path, location.href).href;
    }
    const loaded = await loadPinned(url, pin.sha256);
    return Object.assign({ pinId: pinId, pin: pin, pinsDoc: pinsDoc }, loaded);
  }

  async function fetchSidecarSha256(url) {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      const text = (await res.text()).trim().split(/\s+/)[0].toLowerCase();
      return /^[0-9a-f]{64}$/.test(text) ? text : null;
    } catch (_) {
      return null;
    }
  }

  function viaProxy(url) {
    try {
      const u = new URL(url, location.href);
      if (u.origin === location.origin) return u.href;
      return new URL(
        "/circuit-proxy?url=" + encodeURIComponent(u.href),
        location.href
      ).href;
    } catch (_) {
      return url;
    }
  }

  /**
   * Load remote bytes with pin. Empty expectedSha256 → try .sha256 sidecar (proxied).
   */
  async function loadPinnedRemote(url, expectedSha256, opts) {
    opts = opts || {};
    const useProxy = opts.useProxy !== false;
    let expected = String(expectedSha256 || "")
      .trim()
      .split(/\s+/)[0]
      .toLowerCase();
    const fetchUrl = useProxy ? viaProxy(url) : url;
    if (!/^[0-9a-f]{64}$/.test(expected)) {
      const sideUrl = useProxy ? viaProxy(url.replace(/\?.*$/, "") + ".sha256") : url + ".sha256";
      expected = (await fetchSidecarSha256(sideUrl)) || "";
    }
    if (!/^[0-9a-f]{64}$/.test(expected)) {
      const err = new Error("circuitLoader: missing pin and no .sha256 sidecar");
      err.code = "pin_invalid";
      throw err;
    }
    const loaded = await loadPinned(fetchUrl, expected);
    return Object.assign({ remoteUrl: url }, loaded);
  }

  const api = {
    sha256Hex: sha256Hex,
    loadPinned: loadPinned,
    loadPinnedById: loadPinnedById,
    fetchSidecarSha256: fetchSidecarSha256,
    viaProxy: viaProxy,
    loadPinnedRemote: loadPinnedRemote,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CircuitLoader = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
