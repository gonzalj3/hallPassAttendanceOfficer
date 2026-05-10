import { createHmac, randomUUID } from "node:crypto";
import { createServer } from "node:http";
import { existsSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { pathToFileURL } from "node:url";

import { loadAttendanceCase } from "./src/attendance-data.mjs";
import { appendConversationRows } from "./src/conversation-log.mjs";
import { appendExcuseRecord } from "./src/excuse-log.mjs";
import { buildSessionConfig } from "./src/session-config.mjs";

// In-memory transcript + start-time per call_id so /attendance-excuse
// can ship the full conversation to the backend after the call ends.
// Cleared on successful POST. Maps don't grow unbounded for the demo
// (one active call at a time) — revisit if we ever multiplex.
const callMeta = new Map();

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
  const url = new URL(req.url ?? "/session", `http://${req.headers.host ?? "localhost"}`);
  const scenario = url.searchParams.get("scenario") ?? "absentee";
  const sdp = await readRequestBody(req);
  const form = new FormData();
  form.set("sdp", sdp);
  form.set("session", JSON.stringify(buildSessionConfig(caseData, { scenario })));

  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "OpenAI-Safety-Identifier": process.env.SAFETY_IDENTIFIER ?? "outbound-voice-agent-local"
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

  // Cache transcript turns for the /attendance-excuse handler to ship
  // alongside the excuse summary.
  const meta = callMeta.get(caseData.call_id) ?? {
    startedAt: new Date().toISOString(),
    transcript: []
  };
  for (const m of messages) {
    meta.transcript.push({
      speaker: m.speaker,
      text: m.transcript ?? m.text ?? "",
      occurred_at: m.timestamp ?? m.ts ?? null
    });
  }
  callMeta.set(caseData.call_id, meta);

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

  // Mirror the conversation to the ABE backend so the admin dashboard
  // sees it live. Best-effort: any failure (no backend, no creds, lookup
  // miss, signature mismatch) logs and lets the CSV-only path stand.
  try {
    await postCallToBackend(caseData, body.excuse ?? {});
  } catch (e) {
    console.warn(`[voice-agent] backend POST failed: ${e?.message ?? e}`);
  }
  callMeta.delete(caseData.call_id);

  sendJson(res, 200, result);
}

function signBody(secret, body) {
  return createHmac("sha256", secret).update(body).digest("hex");
}

function inferScenarioFromCase(caseData) {
  // The call_id template is `${student_id}-${absent_date}` for absentee
  // calls; hall-pass scenarios get a HP- prefix on the case CSV. Default
  // to absentee — the backend accepts "other" as a fallback if needed.
  if (typeof caseData?.call_id === "string" && caseData.call_id.startsWith("HP-")) {
    return "hall_pass";
  }
  return "absentee";
}

async function resolveStudentUuid(backendUrl, caseData) {
  const fullName = String(caseData?.student_name ?? "").trim();
  if (!fullName) return null;
  const parts = fullName.split(/\s+/);
  if (parts.length < 2) return null;
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  const url = `${backendUrl}/api/students/lookup?first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}`;
  const response = await fetch(url);
  if (!response.ok) {
    console.warn(`[voice-agent] student lookup ${response.status} for ${fullName}`);
    return null;
  }
  const body = await response.json();
  return body?.id ?? null;
}

async function postCallToBackend(caseData, excuse) {
  const backendUrl = process.env.BACKEND_URL;
  const secret = process.env.BACKEND_HMAC_SECRET;
  if (!backendUrl) {
    // Voice agent runs standalone in CSV-only mode by default. Set
    // BACKEND_URL (quickstart.sh does so when the backend is up) to
    // enable forwarding completed calls. BACKEND_HMAC_SECRET is
    // optional -- if set, the request is signed; if not, we POST
    // unsigned and the backend's hackathon-mode skip lets it through.
    return;
  }

  const studentId = await resolveStudentUuid(backendUrl, caseData);
  if (!studentId) return;

  const meta = callMeta.get(caseData.call_id) ?? {
    startedAt: new Date().toISOString(),
    transcript: []
  };

  const parentConfirmedRaw = excuse?.parent_confirmed;
  const parentConfirmed =
    parentConfirmedRaw === undefined || parentConfirmedRaw === null
      ? null
      : String(parentConfirmedRaw).toLowerCase() === "true" ||
        parentConfirmedRaw === true;

  const payload = {
    correlation_id: randomUUID(),
    student_id: studentId,
    alert_id: null,
    scenario: inferScenarioFromCase(caseData),
    call_started_at: meta.startedAt,
    call_ended_at: new Date().toISOString(),
    transcript: meta.transcript,
    excuse_summary: excuse?.stated_reason ?? excuse?.transcript_summary ?? null,
    parent_confirmed: parentConfirmed,
    language: excuse?.language ?? caseData?.guardian_language ?? null,
    metadata: {
      call_id: caseData?.call_id ?? null,
      excuse_record_id: excuse?.excuse_record_id ?? null
    }
  };

  const body = JSON.stringify(payload);
  const headers = { "Content-Type": "application/json" };
  if (secret) {
    headers["X-HPAO-Signature"] = signBody(secret, body);
  }
  const response = await fetch(`${backendUrl}/v1/agent/inbound/voice-call`, {
    method: "POST",
    headers,
    body
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`backend ${response.status}: ${text.slice(0, 200)}`);
  }
  console.log(
    `[voice-agent] POST /v1/agent/inbound/voice-call ok (correlation_id=${payload.correlation_id})`
  );
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

      if (req.method === "POST" && req.url?.startsWith("/session")) {
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
