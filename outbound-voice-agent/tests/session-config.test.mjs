import assert from "node:assert/strict";
import test from "node:test";

import { loadAttendanceCase } from "../src/attendance-data.mjs";
import { buildSessionConfig, REALTIME_MODEL } from "../src/session-config.mjs";

test("session config uses gpt-realtime-2", () => {
  const config = buildSessionConfig({
    parent_name: "Morgan Johnson",
    guardian_language: "Spanish",
    student_name: "Avery Johnson",
    absences_this_year: 4,
    absent_date: "2026-05-09",
    policy_text: "Students can miss no more than 10 days in a school year.",
    max_absences_per_school_year: 10
  });

  assert.equal(REALTIME_MODEL, "gpt-realtime-2");
  assert.equal(config.model, "gpt-realtime-2");
});

test("session config waits for turn completion before responding", () => {
  const config = buildSessionConfig();

  assert.equal(config.audio.input.turn_detection.type, "semantic_vad");
  assert.equal(config.audio.input.turn_detection.create_response, true);
  assert.equal(config.audio.input.turn_detection.interrupt_response, false);
  assert.equal(config.audio.input.transcription.model, "gpt-4o-transcribe");
});

test("session config keeps responses spoken and compact", () => {
  const config = buildSessionConfig();

  assert.deepEqual(config.output_modalities, ["audio"]);
  assert.equal(config.audio.output.voice, "marin");
  assert.equal(config.reasoning.effort, "low");
  assert.match(config.instructions, /one or two short spoken sentences/);
});

test("session config scripts the attendance call objective", async () => {
  const caseData = await loadAttendanceCase();
  const config = buildSessionConfig(caseData);

  assert.match(config.instructions, /attendance officer/i);
  assert.match(config.instructions, /Required issue sentence for this call/i);
  assert.match(config.instructions, /valid reason/i);
  assert.match(config.instructions, /Spanish/);
  assert.match(config.instructions, /confirm your summary/i);
  assert.match(config.instructions, /submit_attendance_excuse/);
  assert.match(config.instructions, /Avery Johnson/);
  assert.match(config.instructions, /no more than 10 days/);
});

test("session config requires the exact bilingual Ava opening", () => {
  const config = buildSessionConfig({
    parent_name: "Morgan Johnson",
    student_name: "Avery Johnson"
  });

  assert.match(
    config.instructions,
    /Hello this is Ava, your school attendence agent\. Is this Morgan Johnson\?/
  );
  assert.match(config.instructions, /repeat the same opening statement in Spanish/i);
  assert.match(config.instructions, /After confirming the guardian identity, say exactly the full required issue sentence in one speaking turn/i);
  assert.match(config.instructions, /Do not say the issue sentence is missing/i);
  assert.match(config.instructions, /absence or hall pass concern/i);
  assert.match(config.instructions, /language spoken by the person/i);
});

test("session config embeds the selected issue sentence durably", () => {
  const caseData = {
    parent_name: "Morgan Johnson",
    student_name: "Avery Johnson"
  };
  const absenteeConfig = buildSessionConfig(caseData, { scenario: "absentee" });
  const hallPassConfig = buildSessionConfig(caseData, { scenario: "hallPass" });

  assert.match(
    absenteeConfig.instructions,
    /Required issue sentence for this call: "Avery Johnson was absent today and has had 14 hall passes in the last 10 school days for a total of 4 hours absent\. Please tell me, is there a valid reason for the absence and hall passes\?"/
  );
  assert.match(
    hallPassConfig.instructions,
    /Required issue sentence for this call: "Avery Johnson has had 14 hall passes in the last 10 school days for a total of 4 hours absent\. Do you want to share a reason for those hall passes, or should I record that no excuse was provided\?"/
  );
});

test("session config hardens short yes no language detection", () => {
  const config = buildSessionConfig({
    parent_name: "Morgan Johnson",
    guardian_language: "Spanish",
    student_name: "Avery Johnson"
  });

  assert.match(config.instructions, /Language Selection/i);
  assert.match(config.instructions, /Guardian preferred language from the datastore: Spanish/);
  assert.match(config.instructions, /yes.*English/i);
  assert.match(config.instructions, /s[ií].*Spanish/i);
  assert.match(config.instructions, /single-word "no"/i);
  assert.match(config.instructions, /tie-breaker/i);
  assert.match(config.instructions, /¿Prefiere inglés o español\?/i);
});

test("session config exposes a structured excuse submission tool", () => {
  const config = buildSessionConfig();
  const tool = config.tools.find((candidate) => candidate.name === "submit_attendance_excuse");

  assert.equal(config.tool_choice, "auto");
  assert.equal(tool.type, "function");
  assert.equal(tool.parameters.type, "object");
  assert.deepEqual(tool.parameters.required, [
    "absence_dates",
    "stated_reason",
    "parent_confirmed",
    "language",
    "transcript_summary"
  ]);
});
