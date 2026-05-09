# Realtime Voice Turns

A tiny browser prototype for a turn-based attendance-office call with OpenAI Realtime.

The prototype uses `gpt-realtime-2` over WebRTC. The session is configured for turn-based conversation: the parent speaks, Realtime waits for the spoken turn to finish, then the attendance agent responds.

## Setup

```bash
cd /Users/jonathannew/Active-Work/Code/hallPassAttendanceOfficer/realtime-voice-turns
cp .env.example .env
# Add your OpenAI API key to .env
npm start
```

Open `http://localhost:5178`, click **Start Call**, allow microphone access, then respond as the parent. Stop talking and the attendance agent should answer after end-of-turn detection.

The current attendance case is loaded from `data/input/students.csv`, including the guardian's preferred language.
The attendance policy is loaded from `data/input/policies.csv`.
Conversation transcript rows are appended to `data/output/conversations.csv`.
Confirmed parent excuses are appended to `data/output/excuses.csv` with a mocked `pending_review` status.

## Turn-Based Settings

The important session configuration lives in `src/session-config.mjs`:

- `model: "gpt-realtime-2"`
- `audio.input.turn_detection.type: "semantic_vad"`
- `audio.input.turn_detection.create_response: true`
- `audio.input.turn_detection.interrupt_response: false`
- `audio.input.transcription.model: "gpt-4o-transcribe"`
- `reasoning.effort: "low"`
- `tools[0].name: "submit_attendance_excuse"`

The browser handles that Realtime function call by POSTing to `/attendance-excuse`, then sends the tool result back into the Realtime session so the agent can tell the parent the explanation was recorded for attendance-office review.

## Verification

```bash
npm test
```
