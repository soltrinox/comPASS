#!/usr/bin/env node
/**
 * agy-bridge — thin local OpenAI-compatible chat → Google Antigravity CLI (agy).
 *
 * Browser / Wasmer agent → POST http://127.0.0.1:<port>/v1/chat/completions
 * → ENI6MA circuit Gate (digest + ABI probe validate) → spawn `agy --print`
 * → wrap stdout as chat.completion.
 *
 * No provider API keys here; agy uses its own local auth. Bind loopback only.
 */

"use strict";

const { spawn } = require("child_process");
const express = require("express");
const { runCircuitGate } = require("./circuitGate");

const HOST = process.env.AGY_BRIDGE_HOST || "127.0.0.1";
const PORT = Number(process.env.AGY_BRIDGE_PORT || 8791);
const AGY_BIN = process.env.AGY_BIN || "agy";
const AGY_EXTRA_ARGS = (process.env.AGY_EXTRA_ARGS || "")
  .trim()
  .split(/\s+/)
  .filter(Boolean);
/** Default print-mode wait; override with AGY_TIMEOUT_MS (ms). */
const AGY_TIMEOUT_MS = Number(process.env.AGY_TIMEOUT_MS || 5 * 60 * 1000);
const FAIL_OPEN =
  String(process.env.AGY_FAIL_OPEN || "1").toLowerCase() !== "0" &&
  String(process.env.AGY_FAIL_OPEN || "1").toLowerCase() !== "false";

function stripCompass(body) {
  if (!body || typeof body !== "object") return body;
  const out = { ...body };
  delete out.compass;
  delete out.circuit;
  return out;
}

function contentToText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((block) => {
        if (typeof block === "string") return block;
        if (block && typeof block === "object") {
          if (typeof block.text === "string") return block.text;
          if (typeof block.content === "string") return block.content;
        }
        return "";
      })
      .filter(Boolean)
      .join("\n");
  }
  if (content == null) return "";
  return String(content);
}

/** Last user message text from OpenAI-style messages[] (adapter-aligned). */
function extractLastUserMessage(body) {
  const messages = body && Array.isArray(body.messages) ? body.messages : [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (!msg || typeof msg !== "object") continue;
    if (msg.role === "user") {
      const text = contentToText(msg.content).trim();
      if (text) return text;
    }
  }
  for (const key of ["prompt", "input", "text"]) {
    const val = body && body[key];
    if (typeof val === "string" && val.trim()) return val.trim();
  }
  return "";
}

function openaiCompletion({ id, model, content, finishReason, compass }) {
  const now = Math.floor(Date.now() / 1000);
  const out = {
    id: id || `chatcmpl-agy-${now}`,
    object: "chat.completion",
    created: now,
    model: model || "agy",
    choices: [
      {
        index: 0,
        message: { role: "assistant", content: content ?? "" },
        finish_reason: finishReason || "stop",
      },
    ],
    usage: {
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
    },
  };
  if (compass) out.compass = compass;
  return out;
}

function openaiError(message, type, status, compass) {
  const body = {
    error: {
      message: String(message || "agy-bridge error"),
      type: type || "agy_bridge_error",
      param: null,
      code: type || "agy_bridge_error",
    },
  };
  if (compass) body.compass = compass;
  return { status: status || 500, body };
}

/** Run `agy --print <prompt>`, capture stdout/stderr with timeout. */
function runAgy(prompt) {
  return new Promise((resolve) => {
    const args = ["--print", prompt, ...AGY_EXTRA_ARGS];
    const child = spawn(AGY_BIN, args, {
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
      shell: false,
    });

    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };

    const timer = setTimeout(() => {
      try { child.kill("SIGTERM"); } catch (_) {}
      setTimeout(() => {
        try { child.kill("SIGKILL"); } catch (_) {}
      }, 2000);
      finish({
        ok: false,
        code: null,
        signal: "TIMEOUT",
        stdout,
        stderr: (stderr || "") + `\n[agy-bridge] timed out after ${AGY_TIMEOUT_MS}ms`,
      });
    }, AGY_TIMEOUT_MS);

    child.stdout.on("data", (chunk) => { stdout += chunk.toString("utf8"); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
    child.on("error", (err) => {
      finish({
        ok: false,
        code: null,
        signal: null,
        stdout,
        stderr: (stderr || "") + `\n[agy-bridge] spawn error: ${err.message}`,
        spawnError: err,
      });
    });
    child.on("close", (code, signal) => {
      finish({ ok: code === 0, code, signal, stdout, stderr });
    });
  });
}

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "4mb" }));

app.get("/healthz", (_req, res) => {
  res.status(200).json({
    ok: true,
    service: "agy-bridge",
    agy_bin: AGY_BIN,
    bind: `${HOST}:${PORT}`,
    gate: "eni6ma-circuit",
  });
});

app.get("/", (_req, res) => {
  res.status(200).json({
    service: "agy-bridge",
    endpoints: ["GET /healthz", "POST /v1/chat/completions"],
  });
});

app.post("/v1/chat/completions", async (req, res) => {
  const rawBody = req.body && typeof req.body === "object" ? req.body : {};
  // Accept comPASS compass extension then strip before agy (never leak to CLI).
  const body = stripCompass(rawBody);
  const model = typeof body.model === "string" && body.model ? body.model : "agy";

  let gateResult;
  try {
    gateResult = await runCircuitGate(rawBody);
  } catch (e) {
    const status = e && e.status ? e.status : 403;
    const code = e && e.code ? e.code : "compass_gate_denied";
    const compass = e && e.gate ? { gate: e.gate } : undefined;
    const err = openaiError(
      e && e.message ? e.message : "Gate/ENI6MA check failed",
      code,
      status,
      compass
    );
    return res.status(err.status).json(err.body);
  }

  const compassOut = { gate: gateResult.gate };
  if (gateResult.warning) compassOut.gate_warning = gateResult.warning;

  const prompt = extractLastUserMessage(body);
  if (!prompt) {
    const err = openaiError(
      "No user message found in messages[] (or prompt/input/text)",
      "invalid_request_error",
      400,
      compassOut
    );
    return res.status(err.status).json(err.body);
  }

  if (body.stream === true) {
    const err = openaiError(
      "stream=true is not supported by agy-bridge; omit stream or set false",
      "invalid_request_error",
      400,
      compassOut
    );
    return res.status(err.status).json(err.body);
  }

  const result = await runAgy(prompt);
  const text = (result.stdout || "").trimEnd();

  if (result.ok) {
    return res.status(200).json(
      openaiCompletion({
        model,
        content: text || "(agy returned empty stdout)",
        finishReason: "stop",
        compass: compassOut,
      })
    );
  }

  const detail = [
    result.spawnError ? `spawn: ${result.spawnError.message}` : null,
    result.signal ? `signal=${result.signal}` : null,
    result.code != null ? `exit=${result.code}` : null,
    (result.stderr || "").trim() || null,
    text ? `stdout:\n${text}` : null,
  ]
    .filter(Boolean)
    .join("\n");

  if (FAIL_OPEN) {
    const content =
      `[agy-bridge] agy invocation failed (fail-open).\n${detail || "unknown error"}`.trim();
    return res.status(200).json(
      openaiCompletion({ model, content, finishReason: "stop", compass: compassOut })
    );
  }

  const err = openaiError(detail || "agy failed", "agy_cli_error", 502, compassOut);
  return res.status(err.status).json(err.body);
});

app.use((err, _req, res, _next) => {
  const msg = err && err.message ? err.message : "internal error";
  const status = err && err.status ? err.status : 500;
  res.status(status).json(openaiError(msg, "agy_bridge_error", status).body);
});

const server = app.listen(PORT, HOST, () => {
  console.log(`agy-bridge listening on http://${HOST}:${PORT} (AGY_BIN=${AGY_BIN})`);
});

function shutdown(signal) {
  console.log(`agy-bridge shutting down (${signal})`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
