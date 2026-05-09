import assert from "node:assert/strict";
import test from "node:test";

import { loadAttendanceCase } from "../src/attendance-data.mjs";

test("loadAttendanceCase returns student and policy fields", async () => {
  const caseData = await loadAttendanceCase();

  assert.equal(caseData.student_id, "STU-1001");
  assert.equal(caseData.student_name, "Avery Johnson");
  assert.equal(caseData.parent_name, "Morgan Johnson");
  assert.equal(caseData.guardian_language, "Spanish");
  assert.equal(caseData.absences_this_year, 4);
  assert.equal(caseData.max_absences_per_school_year, 10);
  assert.match(caseData.policy_text, /no more than 10 days/);
});
