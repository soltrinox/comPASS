const statusEl = document.getElementById("status");
const outEl = document.getElementById("out");

function setStatus(msg, ok) {
  statusEl.textContent = msg;
  statusEl.className = ok === true ? "ok" : ok === false ? "err" : "";
}

document.getElementById("eni").addEventListener("click", async () => {
  outEl.textContent = "";
  try {
    setStatus("Path-B + proof…");
    const result = await WasmerRunner.runMinimalProof({
      pinsUrl: "../artifacts/pins.json",
    });
    setStatus("Digest OK · proof OK", true);
    outEl.textContent = WasmerRunner.jsonSafe({
      path_b: result.path_b,
      challenge: result.challenge,
      bearings: result.bearings,
      proof: result.proof,
    });
  } catch (e) {
    setStatus(
      e.code === "digest_mismatch" ? "DIGEST MISMATCH — fail closed" : "Error",
      false
    );
    outEl.textContent = e.stack || String(e);
    if (e.expected) {
      outEl.textContent +=
        "\n" +
        JSON.stringify(
          { expected: e.expected, actual: e.actual, bytes: e.bytes },
          null,
          2
        );
    }
  }
});

document.getElementById("compass").addEventListener("click", async () => {
  outEl.textContent = "";
  try {
    setStatus("Verifying compass pin…");
    const pinned = await WasmerRunner.loadCompassPinned("../artifacts/pins.json");
    setStatus("Compass digest OK", true);
    outEl.textContent = JSON.stringify(
      {
        pinId: pinned.pinId,
        sha256: pinned.sha256,
        bytes: pinned.bytes.byteLength,
        path: pinned.pin.path,
      },
      null,
      2
    );
  } catch (e) {
    setStatus("Error", false);
    outEl.textContent = e.stack || String(e);
  }
});
