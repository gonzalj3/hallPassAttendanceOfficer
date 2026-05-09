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
  assert.match(config.instructions, /per-call response instruction/i);
  assert.match(config.instructions, /valid reason/i);
  assert.match(config.instructions, /Spanish/);
  assert.match(config.instructions, /confirm your summary/i);
  assert.match(config.instructions, /submit_attendance_excuse/);
  assert.match(config.instructions, /Avery Johnson/);
  assert.match(config.instructions, /no more than 10 days/);
});

test("session config requires the exact bilingual Abe opening", () => {
  const config = buildSessionConfig({
    parent_name: "Morgan Johnson",
    student_name: "Avery Johnson"
  });

  assert.match(
    config.instructions,
    /Hello this is Abe calling from the Austin High School\. Is this Morgan Johnson\?/
  );
  assert.match(config.instructions, /repeat the same opening statement in Spanish/i);
  assert.match(config.instructions, /After confirming the guardian identity, say only that supplied issue sentence/i);
  assert.match(config.instructions, /absence or hall pass concern/i);
  assert.match(config.instructions, /language spoken by the person/i);
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
