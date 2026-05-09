import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import test from "node:test";

import { loadAttendanceCase } from "../src/attendance-data.mjs";
import { appendExcuseRecord, EXCUSE_LOG_PATH } from "../src/excuse-log.mjs";

async function readExistingFile(pathname) {
  try {
    return await readFile(pathname, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

test("appendExcuseRecord writes structured parent excuse rows to CSV", async () => {
  const originalPath = EXCUSE_LOG_PATH.pathname;
  const backup = await readExistingFile(originalPath);

  try {
    await writeFile(originalPath, "", "utf8");
    const caseData = await loadAttendanceCase();
    const result = await appendExcuseRecord(
      caseData,
      {
        absence_dates: ["2026-05-09"],
        stated_reason: "Avery had a doctor's appointment.",
        parent_confirmed: true,
        language: "Spanish",
        transcript_summary: "Parent said Avery had a doctor's appointment."
      },
      new Date("2026-05-09T12:00:00.000Z")
    );
    const output = await readFile(originalPath, "utf8");

    assert.equal(result.status, "pending_review");
    assert.match(result.excuse_record_id, /^EXC-STU-1001-2026-05-09-/);
    assert.match(output, /excuse_record_id/);
    assert.match(output, /Avery had a doctor's appointment/);
    assert.match(output, /Spanish/);
    assert.match(output, /pending_review/);
  } finally {
    if (backup === null) {
      await writeFile(originalPath, "", "utf8");
    } else {
      await writeFile(originalPath, backup, "utf8");
    }
  }
});
