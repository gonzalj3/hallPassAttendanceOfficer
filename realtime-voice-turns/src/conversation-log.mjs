import { appendFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

import { toCsvRow } from "./csv.mjs";

export const CONVERSATION_LOG_PATH = new URL("../data/output/conversations.csv", import.meta.url);

export async function appendConversationRows(caseData, messages, now = new Date()) {
  await mkdir(dirname(CONVERSATION_LOG_PATH.pathname), { recursive: true });

  const timestamp = now.toISOString();
  const rows = messages
    .filter((message) => message?.speaker && message?.transcript)
    .map((message) =>
      toCsvRow([
        timestamp,
        caseData.call_id,
        caseData.student_id,
        caseData.student_name,
        caseData.parent_name,
        caseData.absences_this_year,
        message.speaker,
        message.transcript
      ])
    );

  if (rows.length === 0) return 0;

  await appendFile(CONVERSATION_LOG_PATH, `${rows.join("\n")}\n`, "utf8");
  return rows.length;
}
