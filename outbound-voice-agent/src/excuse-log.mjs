import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import { toCsvRow } from "./csv.mjs";

export const EXCUSE_LOG_PATH = new URL("../data/output/excuses.csv", import.meta.url);

const header = [
  "timestamp",
  "excuse_record_id",
  "call_id",
  "student_id",
  "student_name",
  "parent_name",
  "guardian_language",
  "absent_date",
  "absence_dates",
  "stated_reason",
  "parent_confirmed",
  "language",
  "transcript_summary",
  "status"
].join(",");

async function ensureExcuseLogFile() {
  await mkdir(dirname(EXCUSE_LOG_PATH.pathname), { recursive: true });

  try {
    const current = await readFile(EXCUSE_LOG_PATH, "utf8");
    if (current.trim()) return;
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }

  await writeFile(EXCUSE_LOG_PATH, `${header}\n`, "utf8");
}

function normalizeAbsenceDates(value, fallbackDate) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).join(";");
  }

  return String(value || fallbackDate || "");
}

export async function appendExcuseRecord(caseData, excuse, now = new Date()) {
  await ensureExcuseLogFile();

  const timestamp = now.toISOString();
  const status = "pending_review";
  const safeDate = String(caseData.absent_date ?? "unknown-date");
  const dateStamp = safeDate.replaceAll(/[^0-9-]/g, "");
  const excuseRecordId = `EXC-${caseData.student_id}-${dateStamp}-${now.getTime()}`;

  const row = toCsvRow([
    timestamp,
    excuseRecordId,
    caseData.call_id,
    caseData.student_id,
    caseData.student_name,
    caseData.parent_name,
    caseData.guardian_language,
    caseData.absent_date,
    normalizeAbsenceDates(excuse.absence_dates, caseData.absent_date),
    excuse.stated_reason,
    Boolean(excuse.parent_confirmed),
    excuse.language || caseData.guardian_language || "English",
    excuse.transcript_summary,
    status
  ]);

  await appendFile(EXCUSE_LOG_PATH, `${row}\n`, "utf8");

  return {
    ok: true,
    status,
    excuse_record_id: excuseRecordId,
    message_for_parent:
      "Thank you. I recorded the explanation and the attendance office will review it."
  };
}
