import { createServer } from "node:http";
import { existsSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { pathToFileURL } from "node:url";

import { loadAttendanceCase } from "./src/attendance-data.mjs";
import { appendConversationRows } from "./src/conversation-log.mjs";
import { appendExcuseRecord } from "./src/excuse-log.mjs";
import { buildSessionConfig } from "./src/session-config.mjs";

function loadEnvFile() {
  const envPath = new URL("./.env", import.meta.url).pathname;
  if (!existsSync(envPath)) return;

  const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const equalsIndex = trimmed.indexOf("=");
    if (equalsIndex === -1) continue;

    const key = trimmed.slice(0, equalsIndex).trim();
    const value = trimmed.slice(equalsIndex + 1).trim().replace(/^["']|["']$/g, "");
    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

loadEnvFile();

const PORT = Number(process.env.PORT ?? 5178);
const PUBLIC_DIR = new URL("./public/", import.meta.url).pathname;
const API_URL = "https://api.openai.com/v1/realtime/calls";

const contentTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8"
};

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, OpenAI-Safety-Identifier",
  "Access-Control-Max-Age": "86400",
  "Cache-Control": "no-store"
};

function sendJson(res, statusCode, body) {
  res.writeHead(statusCode, {
    ...corsHeaders,
    "Content-Type": "application/json; charset=utf-8"
  });
  res.end(JSON.stringify(body));
}

function handleCorsPreflight(res) {
  res.writeHead(204, corsHeaders);
  res.end();
}

async function readRequestBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString("utf8");
}

function getOpenAIKey() {
  const key = process.env.OPENAI_API_KEY;
  if (!key) {
    throw new Error("OPENAI_API_KEY is not set");
  }
  return key;
}

async function createRealtimeCall(req, res) {
  const apiKey = getOpenAIKey();
  const caseData = await loadAttendanceCase();
  const sdp = await readRequestBody(req);
  const form = new FormData();
  form.set("sdp", sdp);
  form.set("session", JSON.stringify(buildSessionConfig(caseData)));

  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "OpenAI-Safety-Identifier": process.env.SAFETY_IDENTIFIER ?? "realtime-voice-turns-local"
    },
    body: form
  });

  const text = await response.text();
  if (!response.ok) {
    res.writeHead(response.status, {
      ...corsHeaders,
      "Content-Type": "application/json; charset=utf-8"
    });
    res.end(text);
    return;
  }

  res.writeHead(200, {
    ...corsHeaders,
    "Content-Type": "application/sdp"
  });
  res.end(text);
}

async function handleCase(req, res) {
  const caseData = await loadAttendanceCase();
  sendJson(res, 200, caseData);
}

async function handleConversationLog(req, res) {
  const rawBody = await readRequestBody(req);
  const body = JSON.parse(rawBody || "{}");
  const caseData = body.caseData ?? (await loadAttendanceCase());
  const messages = Array.isArray(body.messages) ? body.messages : [];
  const rowsWritten = await appendConversationRows(caseData, messages);

  sendJson(res, 200, {
    ok: true,
    rows_written: rowsWritten
  });
}

async function handleAttendanceExcuse(req, res) {
  const rawBody = await readRequestBody(req);
  const body = JSON.parse(rawBody || "{}");
  const caseData = body.caseData ?? (await loadAttendanceCase());
  const result = await appendExcuseRecord(caseData, body.excuse ?? {});

  sendJson(res, 200, result);
}

async function serveStatic(req, res) {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);
  const requestedPath = url.pathname === "/" ? "/index.html" : url.pathname;
  const safePath = normalize(requestedPath).replace(/^(\.\.[/\\])+/, "");
  const filePath = join(PUBLIC_DIR, safePath);

  if (!filePath.startsWith(PUBLIC_DIR)) {
    sendJson(res, 403, { error: "Forbidden" });
    return;
  }

  try {
    const body = await readFile(filePath);
    res.writeHead(200, {
      ...corsHeaders,
      "Content-Type": contentTypes[extname(filePath)] ?? "application/octet-stream"
    });
    res.end(body);
  } catch {
    sendJson(res, 404, { error: "Not found" });
  }
}

export function createAppServer() {
  return createServer(async (req, res) => {
    try {
      if (req.method === "OPTIONS") {
        handleCorsPreflight(res);
        return;
      }

      if (req.method === "POST" && req.url === "/session") {
        await createRealtimeCall(req, res);
        return;
      }

      if (req.method === "GET" && req.url === "/case") {
        await handleCase(req, res);
        return;
      }

      if (req.method === "POST" && req.url === "/conversation-log") {
        await handleConversationLog(req, res);
        return;
      }

      if (req.method === "POST" && req.url === "/attendance-excuse") {
        await handleAttendanceExcuse(req, res);
        return;
      }

      if (req.method === "GET") {
        await serveStatic(req, res);
        return;
      }

      sendJson(res, 405, { error: "Method not allowed" });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      sendJson(res, 500, { error: message });
    }
  });
}

const isMainModule = import.meta.url === pathToFileURL(process.argv[1] ?? "").href;

if (isMainModule) {
  const server = createAppServer();
  server.listen(PORT, () => {
    console.log(`Realtime voice prototype listening on http://localhost:${PORT}`);
  });
}
