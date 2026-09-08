#!/usr/bin/env node
/**
 * Copy @wasmer/sdk dist+pkg into wasmer/browser/vendor so the static
 * appliance (and Docker html root) can dynamic-import the /browser
 * entrypoint without a bundler. Output is gitignored.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, "node_modules", "@wasmer", "sdk");
const DEST = path.join(ROOT, "vendor", "@wasmer", "sdk");

if (!fs.existsSync(path.join(SRC, "dist", "index.js"))) {
  console.warn("vendor-sdk: @wasmer/sdk not installed; skip");
  process.exit(0);
}

fs.rmSync(DEST, { recursive: true, force: true });
fs.mkdirSync(DEST, { recursive: true });
fs.cpSync(SRC, DEST, {
  recursive: true,
  filter: (srcPath) => {
    const base = path.basename(srcPath);
    if (base.endsWith(".map")) return false;
    if (base.endsWith(".d.ts")) return false;
    if (base === "node_modules") return false;
    return true;
  },
});
console.log("vendor-sdk: copied", path.relative(ROOT, DEST));
