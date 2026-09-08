#!/usr/bin/env node
/**
 * B2 — @wasmer/sdk browser boot + Zone A evidence.
 * Isolated page (COOP/COEP) vs fail-open fallback without isolation.
 * Does not fetch compass/decide from the registry (publish NOT_RUN).
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const WASMER = path.join(ROOT, "wasmer");
const OUT_DIR = path.join(ROOT, "test-results", "r-browser-sdk");
const ISOLATED_PORT = Number(process.env.COMPASS_SDK_SMOKE_PORT || 8766);
const FALLBACK_PORT = Number(process.env.COMPASS_SDK_FALLBACK_PORT || 8767);
const RUN_PYTHON = process.env.COMPASS_ZONEA_PYTHON !== "0";

const CSP =
  "default-src 'self'; script-src 'self' 'wasm-unsafe-eval' 'unsafe-eval' blob:; worker-src 'self' blob: 'wasm-unsafe-eval' 'unsafe-eval'; connect-src 'self' http://127.0.0.1:8791 http://localhost:8791 https://raw.githubusercontent.com https://github.com https://objects.githubusercontent.com https://registry.wasmer.io https://cdn.wasmer.io; img-src 'self' data:; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".wasm": "application/wasm",
  ".json": "application/json",
  ".webc": "application/webc",
  ".md": "text/markdown; charset=utf-8",
};

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

function logLine(lines, msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  lines.push(line);
  console.log(line);
}

function isolationHeaders(isolated) {
  const h = {
    "Content-Security-Policy": CSP,
    "Cross-Origin-Resource-Policy": "cross-origin",
  };
  if (isolated) {
    h["Cross-Origin-Opener-Policy"] = "same-origin";
    h["Cross-Origin-Embedder-Policy"] = "require-corp";
  }
  return h;
}

function startStaticServer({ port, isolated, extraFiles }) {
  const extras = extraFiles || {};
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
    if (Object.prototype.hasOwnProperty.call(extras, urlPath)) {
      const filePath = extras[urlPath];
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404, isolationHeaders(isolated));
          res.end("not found extra: " + urlPath);
          return;
        }
        const ext = path.extname(filePath);
        res.writeHead(200, {
          "Content-Type": MIME[ext] || "application/octet-stream",
          ...isolationHeaders(isolated),
        });
        res.end(data);
      });
      return;
    }
    const rel = urlPath === "/" ? "/browser/zonea.html" : urlPath;
    const filePath = path.normalize(path.join(WASMER, rel));
    if (!filePath.startsWith(WASMER)) {
      res.writeHead(403, isolationHeaders(isolated));
      res.end("forbidden");
      return;
    }
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404, isolationHeaders(isolated));
        res.end("not found: " + rel);
        return;
      }
      const ext = path.extname(filePath);
      res.writeHead(200, {
        "Content-Type": MIME[ext] || "application/octet-stream",
        ...isolationHeaders(isolated),
      });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

async function loadPw() {
  const require = createRequire(import.meta.url);
  const name = "play" + "wright";
  const candidates = [
    path.join(WASMER, "browser", "node_modules", name),
    path.join(ROOT, "node_modules", name),
    name,
  ];
  let lastErr;
  for (const c of candidates) {
    try {
      return require(c);
    } catch (e) {
      lastErr = e;
    }
  }
  throw new Error(
    "playwright module missing. From wasmer/browser run npm install, then npx playwright install chromium. " +
      lastErr
  );
}

function buildLocalWebc(lines) {
  const outWebc = path.join(OUT_DIR, "compass-decide-0.1.0.webc");
  if (fs.existsSync(outWebc)) {
    const st = fs.statSync(outWebc);
    logLine(lines, `reusing local webc ${outWebc} bytes=${st.size}`);
    return outWebc;
  }
  const wasmerBin = spawnSync("which", ["wasmer"], { encoding: "utf8" });
  if (wasmerBin.status !== 0) {
    logLine(lines, "webc build NOT_RUN: wasmer CLI not on PATH");
    return null;
  }
  const built = spawnSync(
    "wasmer",
    ["package", "build", "-o", outWebc, "."],
    { cwd: ROOT, encoding: "utf8", maxBuffer: 4 * 1024 * 1024 }
  );
  logLine(
    lines,
    `wasmer package build exit=${built.status} stderr=${(built.stderr || "").trim().slice(0, 400)}`
  );
  if (built.status !== 0 || !fs.existsSync(outWebc)) {
    logLine(lines, "webc build failed; Zone A will use host wasm only");
    return null;
  }
  const st = fs.statSync(outWebc);
  logLine(lines, `local webc ${outWebc} bytes=${st.size}`);
  return outWebc;
}

function dumpHeaders(url, lines, label) {
  return new Promise((resolve) => {
    const u = new URL(url);
    http
      .get(u, (res) => {
        const headers = res.headers;
        logLine(
          lines,
          `${label} status=${res.statusCode} csp=${JSON.stringify(headers["content-security-policy"] || null)} coop=${headers["cross-origin-opener-policy"] || ""} coep=${headers["cross-origin-embedder-policy"] || ""}`
        );
        res.resume();
        resolve({
          status: res.statusCode,
          csp: headers["content-security-policy"] || null,
          coop: headers["cross-origin-opener-policy"] || null,
          coep: headers["cross-origin-embedder-policy"] || null,
          corp: headers["cross-origin-resource-policy"] || null,
        });
      })
      .on("error", (e) => {
        logLine(lines, `${label} header dump failed: ${e}`);
        resolve({ error: String(e) });
      });
  });
}

async function launchBrowser(pw, lines) {
  const chromium = pw.chromium;
  const channel = process.env.COMPASS_SMOKE_CHANNEL || (process.env.CI ? undefined : "chrome");
  const launchOpts = { headless: true };
  if (channel) launchOpts.channel = channel;
  try {
    const browser = await chromium.launch(launchOpts);
    logLine(lines, `launched headless channel=${channel || "bundled"}`);
    return browser;
  } catch (e) {
    const browser = await chromium.launch({ headless: true });
    logLine(lines, "launched bundled after channel failure: " + e);
    return browser;
  }
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const ts = stamp();
  const lines = [];
  const evidence = {
    stage: "B2",
    target: "browser-@wasmer/sdk",
    recorded_at: new Date().toISOString(),
    grade: "NOT_RUN",
    pass: false,
    csp: CSP,
    python_pin: "python/python@=3.13.18",
    sdk_npm: "0.11.0",
    registry_compass: "NOT_RUN",
    cases: {},
    blocker: null,
  };

  const webcPath = buildLocalWebc(lines);
  const extraFiles = {};
  if (webcPath) {
    extraFiles["/artifacts/compass-decide-0.1.0.webc"] = webcPath;
  }

  let isolatedServer;
  let fallbackServer;
  try {
    isolatedServer = await startStaticServer({
      port: ISOLATED_PORT,
      isolated: true,
      extraFiles,
    });
    fallbackServer = await startStaticServer({
      port: FALLBACK_PORT,
      isolated: false,
      extraFiles: {},
    });
    logLine(lines, `isolated http://127.0.0.1:${ISOLATED_PORT}/`);
    logLine(lines, `fallback  http://127.0.0.1:${FALLBACK_PORT}/`);
  } catch (e) {
    evidence.blocker = "static_server: " + String(e);
    writeOut(ts, evidence, lines);
    process.exitCode = 2;
    return;
  }

  evidence.cases.isolated_headers = await dumpHeaders(
    `http://127.0.0.1:${ISOLATED_PORT}/browser/zonea.html`,
    lines,
    "isolated zonea.html"
  );
  evidence.cases.fallback_headers = await dumpHeaders(
    `http://127.0.0.1:${FALLBACK_PORT}/browser/index.html`,
    lines,
    "fallback index.html"
  );

  let pw;
  try {
    pw = await loadPw();
  } catch (e) {
    evidence.blocker = String(e);
    evidence.grade = "NOT_RUN";
    logLine(lines, "BLOCKER: " + evidence.blocker);
    writeOut(ts, evidence, lines);
    isolatedServer.close();
    fallbackServer.close();
    process.exitCode = 2;
    return;
  }

  let browser;
  try {
    browser = await launchBrowser(pw, lines);
  } catch (e) {
    evidence.blocker = "browser_launch_failed: " + String(e);
    evidence.grade = "NOT_RUN";
    logLine(lines, "BLOCKER: " + evidence.blocker);
    writeOut(ts, evidence, lines);
    isolatedServer.close();
    fallbackServer.close();
    process.exitCode = 2;
    return;
  }

  try {
    const page = await browser.newPage();
    page.on("console", (msg) => logLine(lines, `isolated console.${msg.type()}: ${msg.text()}`));
    page.on("pageerror", (err) => logLine(lines, "isolated pageerror: " + err));
    page.on("response", (res) => {
      if (res.status() >= 400) {
        logLine(lines, `isolated http ${res.status()} ${res.url()}`);
      }
    });
    const pythonQ = RUN_PYTHON ? "python=1" : "python=0";
    const url = `http://127.0.0.1:${ISOLATED_PORT}/browser/zonea.html?${pythonQ}`;
    logLine(lines, "goto " + url);
    const nav = await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    evidence.cases.isolated_nav_csp = nav ? nav.headers()["content-security-policy"] : null;
    const pythonTimeout = RUN_PYTHON ? 300000 : 90000;
    await page.waitForFunction(
      () => ["1", "0"].includes(document.documentElement.dataset.zoneaDone),
      null,
      { timeout: pythonTimeout }
    );
    const isolatedEval = await page.evaluate(() => ({
      isolated: window.crossOriginIsolated === true,
      ready: document.documentElement.dataset.zoneaReady,
      sdk: document.documentElement.dataset.zoneaSdk,
      host: document.documentElement.dataset.zoneaHost,
      webc: document.documentElement.dataset.zoneaWebc,
      python: document.documentElement.dataset.zoneaPython,
      report: window.__COMPASS_ZONEA__ ? window.__COMPASS_ZONEA__.report() : null,
      sharedArrayBuffer: typeof SharedArrayBuffer !== "undefined",
    }));
    evidence.cases.isolated = isolatedEval;
    logLine(
      lines,
      `isolated crossOriginIsolated=${isolatedEval.isolated} sdk=${isolatedEval.sdk} host=${isolatedEval.host} webc=${isolatedEval.webc} python=${isolatedEval.python}`
    );

    const fb = await browser.newPage();
    fb.on("console", (msg) => logLine(lines, `fallback console.${msg.type()}: ${msg.text()}`));
    const fbUrl = `http://127.0.0.1:${FALLBACK_PORT}/browser/index.html?smoke=1`;
    await fb.goto(fbUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    await fb.waitForFunction(
      () => ["1", "0"].includes(document.documentElement.dataset.smokeReady),
      null,
      { timeout: 60000 }
    );
    const fallbackEval = await fb.evaluate(() => ({
      isolated: window.crossOriginIsolated === true,
      ready: document.documentElement.dataset.smokeReady,
      sdk: window.__COMPASS_SDK__ || null,
      fixture: window.__COMPASS_SMOKE__ ? window.__COMPASS_SMOKE__.decideFixture() : null,
    }));
    evidence.cases.fallback = fallbackEval;
    const fallbackOk =
      fallbackEval.isolated === false &&
      fallbackEval.ready === "1" &&
      fallbackEval.fixture &&
      fallbackEval.fixture.fail_open === false &&
      fallbackEval.fixture.selected_model_version_id === "urn:mg:model:cheap";
    logLine(
      lines,
      `fallback isolated=${fallbackEval.isolated} ready=${fallbackEval.ready} sdk_skipped=${fallbackEval.sdk && fallbackEval.sdk.skipped} fixture=${fallbackEval.fixture && fallbackEval.fixture.selected_model_version_id}`
    );

    const hostOk = isolatedEval.report && isolatedEval.report.compass_host.grade === "FULL";
    const sdkBooted = isolatedEval.isolated === true && isolatedEval.sdk === "1";
    const webcGrade = isolatedEval.report && isolatedEval.report.compass_webc.grade;
    const pythonGrade = isolatedEval.report && isolatedEval.report.python.grade;
    const registryFake = isolatedEval.report && isolatedEval.report.registry_compass.attempted === true;

    if (registryFake) {
      evidence.grade = "FAIL";
      evidence.blocker = "registry compass fetch was attempted; forbidden while publish is NOT_RUN";
    } else if (hostOk && fallbackOk && sdkBooted && isolatedEval.isolated === true) {
      // compass/decide is unpublished — Zone A is PARTIAL even when local
      // webc + python/python registry succeed. Do not claim FULL.
      evidence.grade = "PARTIAL";
      evidence.pass = true;
      evidence.blocker =
        pythonGrade === "FULL" && webcGrade === "FULL"
          ? "compass/decide registry fetch NOT_RUN (publish blocked); local webc + python/python@=3.13.18 succeeded"
          : "SDK booted against local guest; registry compass/decide NOT_RUN";
    } else if (hostOk && fallbackOk) {
      evidence.grade = "PARTIAL";
      evidence.pass = true;
      evidence.blocker =
        "SDK/python/webc not fully green; host compass_decide_json + fail-open fallback passed";
    } else {
      evidence.grade = "PARTIAL";
      evidence.pass = false;
      evidence.blocker = "host decide or fallback failed";
    }
    logLine(lines, `RESULT grade=${evidence.grade} pass=${evidence.pass} python=${pythonGrade} webc=${webcGrade}`);
  } catch (e) {
    evidence.blocker = "smoke_runtime: " + String(e);
    evidence.grade = "PARTIAL";
    evidence.pass = false;
    logLine(lines, "ERROR: " + evidence.blocker);
  } finally {
    await browser.close();
    isolatedServer.close();
    fallbackServer.close();
  }

  writeOut(ts, evidence, lines);
  process.exitCode = evidence.pass ? 0 : 1;
}

function writeOut(ts, evidence, lines) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const logPath = path.join(OUT_DIR, `sdk-boot-${ts}.log.txt`);
  fs.writeFileSync(logPath, lines.join("\n") + "\n");
  fs.writeFileSync(path.join(OUT_DIR, "evidence.json"), JSON.stringify(evidence, null, 2) + "\n");
  fs.writeFileSync(path.join(OUT_DIR, "sdk-boot.txt"), lines.join("\n") + "\n");
  evidence.log = path.relative(ROOT, logPath);
}

main().catch((e) => {
  console.error(e);
  process.exit(2);
});
