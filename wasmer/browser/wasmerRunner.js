/* Digest-pinned ENI6MA minimal-proof runner (Gate stub precursor).
 * Path-B verifies published wasm bytes; runtime uses wasm-bindgen pkg glue.
 */
(function (root) {
  const jsonSafe = (v) =>
    JSON.stringify(v, (_k, x) => (typeof x === "bigint" ? x.toString() : x), 2);

  /**
   * @param {object} opts
   * @param {string} opts.pinsUrl - e.g. ../artifacts/pins.json
   * @param {string} [opts.pinId] - default eni6ma_demo_wasm_v1
   * @param {string} [opts.pkgBase] - directory with eni6ma_wasm.js (default demo-wasm pkg)
   * @param {string} [opts.challengeJson]
   * @param {string} [opts.bearingsJson]
   */
  async function runMinimalProof(opts) {
    opts = opts || {};
    const loader = root.CircuitLoader;
    if (!loader) throw new Error("wasmerRunner: CircuitLoader missing");

    const pinId = opts.pinId || "eni6ma_demo_wasm_v1";
    const pinsUrl = opts.pinsUrl || "../artifacts/pins.json";
    const pinned = await loader.loadPinnedById(pinsUrl, pinId);

    // Gate path will wrap this; for now Path-B gate is the digest check above.
    const pkgBase =
      opts.pkgBase ||
      new URL("../artifacts/eni6ma/demo-wasm/v1/pkg/", location.href).href;
    const mod = await import(pkgBase + "eni6ma_wasm.js");
    await mod.default();
    const challenge =
      opts.challengeJson ||
      JSON.stringify({
        timestamp: 12345,
        matrix_data: {
          rows: [{ values: [1, 2, 3], row_hash: "x", row_index: 0 }],
        },
      });
    const bearings = opts.bearingsJson || JSON.stringify(["U", "L", "R", "U"]);
    const proof = mod.build_minimal_proof(challenge, bearings);

    return {
      path_b: {
        pinId: pinned.pinId,
        expected: pinned.pin.sha256,
        actual: pinned.sha256,
        published_bytes: pinned.bytes.byteLength,
        source_ref: pinned.pin.source_ref || null,
      },
      challenge: JSON.parse(challenge),
      bearings: JSON.parse(bearings),
      proof: proof,
      jsonSafe: jsonSafe,
    };
  }

  /**
   * Verify compass Route WASM against pins before instantiate (optional harden).
   */
  async function loadCompassPinned(pinsUrl) {
    const loader = root.CircuitLoader;
    if (!loader) throw new Error("wasmerRunner: CircuitLoader missing");
    return loader.loadPinnedById(
      pinsUrl || "../artifacts/pins.json",
      "compass_core_bg.wasm"
    );
  }

  const api = {
    runMinimalProof: runMinimalProof,
    loadCompassPinned: loadCompassPinned,
    jsonSafe: jsonSafe,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.WasmerRunner = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
