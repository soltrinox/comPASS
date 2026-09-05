#!/usr/bin/env node
/**
 * Track J — headless browser smoke for wasmer/browser/.
 * Loads compass_core_bg.wasm via the sandbox page and exercises decide() + fail-open.
 * No provider keys. Writes evidence under test-results/j-wasmer-packaging/.
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const WASMER = path.join(ROOT, "wasmer");
const OUT_DIR = path.join(ROOT, "test-results", "j-wasmer-packaging");
const PORT = Number(process.env.COMPASS_SMOKE_PORT || 8765);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".wasm": "application/wasm",
  ".json": "application/json",
  ".md": "text/markdown; charset=utf-8",
};

function logLine(lines, msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  lines.push(line);
  console.log(line);
}

function startStaticServer() {
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
    const rel = urlPath === "/" ? "/browser/index.html" : urlPath;
    const filePath = path.normalize(path.join(WASMER, rel));
    if (!filePath.startsWith(WASMER)) { res.writeHead(403); res.end("forbidden"); return; }
    fs.readFile(filePath, (err, data) => {
      if (err) { res.writeHead(404); res.end("not found: " + rel); return; }
      const ext = path.extname(filePath);
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      res.end(data);
    });
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(PORT, "127.0.0.1", () => resolve(server));
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
    try { return require(c); } catch (e) { lastErr = e; }
  }
  throw new Error("playwright module missing. From wasmer/browser run package-manager install, then browser install chromium. " + lastErr);
}

function writeOut(outDir, evidence, lines) {
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, "browser-smoke.json"), JSON.stringify(evidence, null, 2) + "\n");
  fs.writeFileSync(path.join(outDir, "browser-smoke.txt"), lines.join("\n") + "\n");
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const lines = [];
  const evidence = {
    track: "J",
    target: "browser-headless",
    recorded_at: new Date().toISOString(),
    grade: "NOT_RUN",
    pass: false,
    cases: {},
    blocker: null,
  };
  let server;
  try {
    server = await startStaticServer();
    logLine(lines, `static server on http://127.0.0.1:${PORT}/`);
  } catch (e) {
    evidence.blocker = "static_server: " + String(e);
    writeOut(OUT_DIR, evidence, lines);
    process.exitCode = 2;
    return;
  }
  let pw;
  try { pw = await loadPw(); }
  catch (e) {
    evidence.blocker = String(e);
    evidence.grade = "NOT_RUN";
    logLine(lines, "BLOCKER: " + evidence.blocker);
    writeOut(OUT_DIR, evidence, lines);
    server.close();
    process.exitCode = 2;
    return;
  }
  const chromium = pw.chromium;
  const channel = process.env.COMPASS_SMOKE_CHANNEL || (process.env.CI ? undefined : "chrome");
  const launchOpts = { headless: true };
  if (channel) launchOpts.channel = channel;
  let browser;
  try {
    browser = await chromium.launch(launchOpts);
    logLine(lines, `launched headless channel=${channel || "bundled"}`);
  } catch (e) {
    try {
      browser = await chromium.launch({ headless: true });
      logLine(lines, "launched bundled after channel failure: " + e);
    } catch (e2) {
      evidence.blocker = "browser_launch_failed: " + String(e2);
      evidence.grade = "NOT_RUN";
      logLine(lines, "BLOCKER: " + evidence.blocker);
      writeOut(OUT_DIR, evidence, lines);
      server.close();
      process.exitCode = 2;
      return;
    }
  }
  try {
    const page = await browser.newPage();
    const url = `http://127.0.0.1:${PORT}/browser/index.html?smoke=1`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForFunction(() => ["1","0"].includes(document.documentElement.dataset.smokeReady), null, { timeout: 60000 });
    const readyFlag = await page.evaluate(() => document.documentElement.dataset.smokeReady);
    if (readyFlag !== "1") {
      const err = await page.evaluate(() => document.documentElement.dataset.smokeError || document.documentElement.dataset.smokeStatus);
      throw new Error("module not ready: " + err);
    }
    logLine(lines, "module ready");
    const fixture = await page.evaluate(() => window.__COMPASS_SMOKE__.decideFixture());
    evidence.cases.fixture = fixture;
    const fixtureOk = fixture && fixture.fail_open === false && fixture.selected_model_version_id === "urn:mg:model:cheap";
    logLine(lines, `fixture decide: ok=${fixtureOk} selected=${fixture && fixture.selected_model_version_id}`);
    const missing = await page.evaluate(() => window.__COMPASS_SMOKE__.decideMissing());
    evidence.cases.missing = missing;
    const missingOk = missing && missing.default_reason === "snapshot_missing" && missing.fail_open === true;
    logLine(lines, `missing fail-open: ok=${missingOk}`);
    const corrupt = await page.evaluate(() => window.__COMPASS_SMOKE__.decideCorrupt());
    evidence.cases.corrupt = corrupt;
    const corruptOk = corrupt && corrupt.default_reason === "snapshot_corrupt" && corrupt.fail_open === true;
    logLine(lines, `corrupt fail-open: ok=${corruptOk}`);
    const importCheck = await page.evaluate(async () => {
      const res = await fetch("../artifacts/compass_core_bg.wasm");
      const buf = await res.arrayBuffer();
      const mod = await WebAssembly.compile(buf);
      const imports = WebAssembly.Module.imports(mod);
      return {
        importCount: imports.length,
        forbidden: imports.filter((im) => im.module === "keys" || im.name === "fetch" || String(im.name).includes("fetch")),
      };
    });
    evidence.cases.imports = importCheck;
    const importsOk = importCheck.importCount === 0 && importCheck.forbidden.length === 0;
    logLine(lines, `import table empty: ok=${importsOk} count=${importCheck.importCount}`);
    evidence.pass = Boolean(fixtureOk && missingOk && corruptOk && importsOk);
    evidence.grade = evidence.pass ? "FULL" : "PARTIAL";
    if (!evidence.pass) evidence.blocker = "one or more smoke assertions failed";
    logLine(lines, `RESULT grade=${evidence.grade} pass=${evidence.pass}`);
  } catch (e) {
    evidence.blocker = "smoke_runtime: " + String(e);
    evidence.grade = "PARTIAL";
    evidence.pass = false;
    logLine(lines, "ERROR: " + evidence.blocker);
  } finally {
    await browser.close();
    server.close();
  }
  writeOut(OUT_DIR, evidence, lines);
  process.exitCode = evidence.pass ? 0 : 1;
}

main().catch((e) => { console.error(e); process.exit(2); });
