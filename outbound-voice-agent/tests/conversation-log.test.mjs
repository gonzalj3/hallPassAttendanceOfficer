import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { loadAttendanceCase } from "../src/attendance-data.mjs";
import { appendConversationRows, CONVERSATION_LOG_PATH } from "../src/conversation-log.mjs";

test("appendConversationRows writes utterance rows to CSV", async () => {
  const tempDir = await mkdtemp(join(tmpdir(), "attendance-log-"));
  const originalPath = CONVERSATION_LOG_PATH.pathname;
  const backup = await readFile(originalPath, "utf8");

  try {
    await writeFile(originalPath, "timestamp,call_id,student_id,student_name,parent_name,absences_this_year,speaker,transcript\n", "utf8");
    const caseData = await loadAttendanceCase();
    const written = await appendConversationRows(
      caseData,
      [
        { speaker: "assistant", transcript: "Hello, this is the attendance office." },
        { speaker: "parent", transcript: "Avery had a doctor's appointment." }
      ],
      new Date("2026-05-09T12:00:00.000Z")
    );
    const output = await readFile(originalPath, "utf8");

    assert.equal(written, 2);
    assert.match(output, /STU-1001/);
    assert.match(output, /assistant/);
    assert.match(output, /doctor's appointment/);
  } finally {
    await writeFile(originalPath, backup, "utf8");
    await rm(tempDir, { recursive: true, force: true });
  }
});
