# Submission Info

## Project Title

Ava Attendance Officer

## 1-Sentence Tagline

A multilingual school attendance agent that closes the loop between classroom attendence, school policy, and guardian communication.


## Track Selected

Agents Track

## Loom Video Link

[Placeholder: loom.com video link]

## Repo Link

https://github.com/gonzalj3/hallPassAttendanceOfficer

## README Link

https://github.com/gonzalj3/hallPassAttendanceOfficer/blob/main/README.md

## Deployed URL

[Placeholder: deployed app URL, if any]

## Team Roster

- Juliana Messineo - iPad App
- Chrissy McDannell - Teacher Dashboard
- Jose Gonzalez - Data, Policy, and Logic
- Jonathan Malkin - Realtime voice agent

## Short Write-Up

School funding is based, in part, on student attendence.  Tracking time outside class is often not tracked properly and has minimal follow-up. The Ava Agent provides a simple way to track time, identify issues, and communicate with student guardians.  

The prototype connects a teacher dashboard, hall-pass iPad flow, FastAPI/Postgres policy backend, alerts, and an OpenAI Realtime voice agent into one working demo.

Teacher attendance records and student hall-pass activity flow into a shared backend where Ava maintains the student timeline, evaluates policy thresholds, and raises alerts when intervention is needed. When a student’s attendance or hall-pass pattern needs guardian context, Ava places a bilingual voice call, asks for a reason, summarizes the response, and records the explanation for attendance-office review. 

The result is a practical school operations agent: less manual follow-up, clearer documentation, and faster visibility into which students need support.