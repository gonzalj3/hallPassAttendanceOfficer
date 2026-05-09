import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import test from "node:test";

import { createAppServer } from "../server.mjs";
import { EXCUSE_LOG_PATH } from "../src/excuse-log.mjs";

async function readExistingFile(pathname) {
  try {
    return await readFile(pathname, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

function listen(server) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      server.off("error", reject);
      const address = server.address();
      resolve(`http://127.0.0.1:${address.port}`);
    });
  });
}

function close(server) {
  return new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

test("E2E: loads a case and records a confirmed attendance excuse over HTTP", async () => {
  const backup = await readExistingFile(EXCUSE_LOG_PATH.pathname);
  const server = createAppServer();

  try {
    await writeFile(EXCUSE_LOG_PATH.pathname, "", "utf8");
    const baseUrl = await listen(server);

    const caseResponse = await fetch(`${baseUrl}/case`);
    assert.equal(caseResponse.status, 200);
    const caseData = await caseResponse.json();
    assert.equal(caseData.student_id, "STU-1001");
    assert.equal(caseData.guardian_language, "Spanish");

    const excuseResponse = await fetch(`${baseUrl}/attendance-excuse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        caseData,
        excuse: {
          absence_dates: [caseData.absent_date],
          stated_reason: "Avery had a doctor's appointment.",
          parent_confirmed: true,
          language: "Spanish",
          transcript_summary: "Parent confirmed Avery had a doctor's appointment."
        }
      })
    });

    assert.equal(excuseResponse.status, 200);
    const result = await excuseResponse.json();
    assert.equal(result.ok, true);
    assert.equal(result.status, "pending_review");
    assert.match(result.excuse_record_id, /^EXC-STU-1001-2026-05-09-/);

    const output = await readFile(EXCUSE_LOG_PATH.pathname, "utf8");
    assert.match(output, /excuse_record_id/);
    assert.match(output, /Avery had a doctor's appointment/);
    assert.match(output, /pending_review/);
  } finally {
    await close(server);
    if (backup === null) {
      await writeFile(EXCUSE_LOG_PATH.pathname, "", "utf8");
    } else {
      await writeFile(EXCUSE_LOG_PATH.pathname, backup, "utf8");
    }
  }
});
