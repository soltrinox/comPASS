#!/usr/bin/env node
"use strict";
function extractPrompt(argv) {
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--print" || a === "-p") {
      const next = argv[i + 1];
      if (next != null && !String(next).startsWith("-")) return String(next);
      return "";
    }
    if (a.startsWith("--print=")) return a.slice("--print=".length);
    if (a.startsWith("-p=") && a.length > 3) return a.slice(3);
  }
  for (const a of argv) {
    if (a && !String(a).startsWith("-")) return String(a);
  }
  return "";
}
const prompt = extractPrompt(process.argv.slice(2));
const echo = prompt ? prompt.slice(0, 200) : "(empty prompt)";
process.stdout.write("[fake-agy] ok\n" + echo + "\n");
process.exit(0);
