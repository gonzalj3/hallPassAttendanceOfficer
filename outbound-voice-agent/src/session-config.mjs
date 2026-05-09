export const REALTIME_MODEL = "gpt-realtime-2";

export const CALL_SCENARIOS = {
  absentee: {
    label: "absentee",
    issueSentence: (caseData) =>
      `${caseData?.student_name ?? "The student"} was absent today. Please tell me, is there a valid reason for the absence?`
  },
  hallPass: {
    label: "hall pass",
    issueSentence: (caseData) =>
      `${caseData?.student_name ?? "The student"} has had 14 hall passes in the last 10 school days for a total of 4 hours absent. Do you want to share a reason for those hall passes, or should I record that no excuse was provided?`
  }
};

export function getCallScenario(scenario) {
  return CALL_SCENARIOS[scenario] ?? CALL_SCENARIOS.absentee;
}

function buildAttendanceInstructions(caseData = {}, options = {}) {
  const studentName = caseData.student_name ?? "the student";
  const parentName = caseData.parent_name ?? "the parent or guardian";
  const guardianLanguage = caseData.guardian_language ?? "unknown";
  const absencesThisYear = caseData.absences_this_year ?? "the recorded";
  const policyText =
    caseData.policy_text ?? "Students can miss no more than 10 days in a school year.";
  const maxAbsences = caseData.max_absences_per_school_year ?? 10;
  const scenario = getCallScenario(options.scenario);
  const issueSentence = scenario.issueSentence(caseData);

  return [
    "# Role and Objective",
    "You are a school attendance officer making a short turn-based call to a parent or guardian.",
    `You are calling ${parentName} about ${studentName}.`,
    `The student has ${absencesThisYear} absences this school year.`,
    `Attendance policy: ${policyText}`,
    `Policy limit: no more than ${maxAbsences} days missed in a school year.`,
    "",
    "# Call Flow",
    `Start every new or reset call with this exact English opening: "Hello this is Abe calling from the Austin High School. Is this ${parentName}?"`,
    "Immediately after the English opening, repeat the same opening statement in Spanish.",
    "After the bilingual guardian identity check, use the appropriate language for the rest of the call based on the language spoken by the person.",
    `Selected call scenario: ${scenario.label}.`,
    `Required issue sentence for this call: "${issueSentence}"`,
    "After confirming the guardian identity, say exactly the full required issue sentence in one speaking turn, then wait for the guardian response.",
    "Do not say the issue sentence is missing. If you need the issue sentence, use the Required issue sentence line above.",
    "Do not replace the required issue sentence with a different absence or hall pass concern.",
    "Wait for the parent to finish before responding.",
    "If the parent gives an excuse, summarize it in one sentence and ask them to confirm your summary.",
    "Only after the parent confirms, call submit_attendance_excuse with the confirmed reason.",
    "If the parent says there is no excuse, call submit_attendance_excuse with stated_reason set to no excuse provided and parent_confirmed set to true.",
    "After submit_attendance_excuse returns, briefly tell the parent the result and end politely.",
    "Do not ask extra follow-up questions unless the audio is unclear or the parent did not answer the question.",
    "",
    "# Language Selection",
    `Guardian preferred language from the datastore: ${guardianLanguage}.`,
    'If the guardian response is "yes", continue in English.',
    'If the guardian response is "sí", "si", "claro", or another Spanish acknowledgement, continue in Spanish.',
    'Treat a single-word "no" as ambiguous for language because it can be English or Spanish; use the datastore preferred language as the tie-breaker when available.',
    'If a short response is unclear and there is no datastore tie-breaker, ask once: "Would you prefer English or Spanish? ¿Prefiere inglés o español?"',
    "If the guardian later speaks a different language, switch immediately to that language.",
    "When calling submit_attendance_excuse, set language to the language used for the substantive reason, not merely the bilingual opening.",
    "",
    "# Turn Taking",
    "Wait until the parent has finished speaking before responding.",
    "Do not interrupt the parent. If they pause briefly, allow the turn detector to decide whether they are done.",
    "",
    "# Verbosity",
    "Default to one or two short spoken sentences.",
    "Ask one concise clarification question when audio is unclear or the response is ambiguous.",
    "",
    "# Reasoning",
    "For this prototype, keep reasoning minimal and stay on script."
  ].join("\n");
}

const submitAttendanceExcuseTool = {
  type: "function",
  name: "submit_attendance_excuse",
  description: "Record the parent or guardian's confirmed explanation for an attendance or hall pass concern.",
  parameters: {
    type: "object",
    properties: {
      absence_dates: {
        type: "array",
        items: { type: "string" },
        description: "Absence dates discussed in YYYY-MM-DD format when known."
      },
      stated_reason: {
        type: "string",
        description: "The parent or guardian's confirmed explanation."
      },
      parent_confirmed: {
        type: "boolean",
        description: "Whether the parent or guardian confirmed the summary before submission."
      },
      language: {
        type: "string",
        description: "Language used for the parent or guardian conversation."
      },
      transcript_summary: {
        type: "string",
        description: "Brief neutral summary of the relevant exchange."
      }
    },
    required: [
      "absence_dates",
      "stated_reason",
      "parent_confirmed",
      "language",
      "transcript_summary"
    ]
  }
};

export function buildSessionConfig(caseData, options = {}) {
  return {
    type: "realtime",
    model: REALTIME_MODEL,
    output_modalities: ["audio"],
    audio: {
      input: {
        transcription: {
          model: "gpt-4o-transcribe"
        },
        turn_detection: {
          type: "semantic_vad",
          create_response: true,
          interrupt_response: false
        }
      },
      output: {
        voice: "marin"
      }
    },
    reasoning: {
      effort: "low"
    },
    tools: [submitAttendanceExcuseTool],
    tool_choice: "auto",
    instructions: buildAttendanceInstructions(caseData, options)
  };
}
