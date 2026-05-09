import { readFile } from "node:fs/promises";

import { parseCsv } from "./csv.mjs";

const STUDENTS_PATH = new URL("../data/input/students.csv", import.meta.url);
const POLICIES_PATH = new URL("../data/input/policies.csv", import.meta.url);

export async function loadAttendanceCase() {
  const [studentText, policyText] = await Promise.all([
    readFile(STUDENTS_PATH, "utf8"),
    readFile(POLICIES_PATH, "utf8")
  ]);

  const [student] = parseCsv(studentText);
  const [policy] = parseCsv(policyText);

  if (!student) {
    throw new Error("No students found in data/input/students.csv");
  }

  if (!policy) {
    throw new Error("No policies found in data/input/policies.csv");
  }

  return {
    call_id: `${student.student_id}-${student.absent_date}`,
    student_id: student.student_id,
    student_name: `${student.student_first_name} ${student.student_last_name}`,
    parent_name: student.parent_name,
    parent_phone: student.parent_phone,
    guardian_language: student.guardian_language || "English",
    absences_this_year: Number(student.absences_this_year),
    absent_date: student.absent_date,
    policy_id: policy.policy_id,
    policy_name: policy.policy_name,
    policy_text: policy.policy_text,
    max_absences_per_school_year: Number(policy.max_absences_per_school_year)
  };
}
