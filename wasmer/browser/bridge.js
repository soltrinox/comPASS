/* comPASS browser egress bridge — allowlist for proxy_override hosts (ADR 0006).
 * Deny-by-default when allowlist is a non-empty array.
 */
(function (root) {
  function normalizeHost(host) {
    return String(host || "")
      .toLowerCase()
      .replace(/^\./, "");
  }

  /**
   * @param {string} url
   * @param {string[]|null|undefined} allowlist - null/undefined = allow all (dev);
   *        [] = deny all; otherwise exact or subdomain match.
   */
  function hostAllowed(url, allowlist) {
    if (allowlist == null) return true;
    if (!allowlist.length) return false;
    let host = "";
    try {
      host = new URL(url).hostname.toLowerCase();
    } catch (_) {
      return false;
    }
    return allowlist.some(function (entry) {
      const e = normalizeHost(entry);
      return host === e || host.endsWith("." + e);
    });
  }

  /**
   * Forward JSON to an override URL only if allowlisted.
   * @returns {Promise<Response>}
   */
  async function forwardChatCompletions(url, body, allowlist, init) {
    if (!hostAllowed(url, allowlist)) {
      const err = new Error("compass_bridge: host not allowlisted");
      err.code = "proxy_host_denied";
      throw err;
    }
    const payload =
      body && typeof body === "object" ? Object.assign({}, body) : body;
    if (payload && typeof payload === "object" && "compass" in payload) {
      delete payload.compass;
    }
    return fetch(url, {
      method: "POST",
      headers: Object.assign(
        { "Content-Type": "application/json", Accept: "application/json" },
        (init && init.headers) || {}
      ),
      body: typeof payload === "string" ? payload : JSON.stringify(payload),
      signal: init && init.signal,
    });
  }

  const api = { hostAllowed: hostAllowed, forwardChatCompletions: forwardChatCompletions };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.CompassBridge = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
