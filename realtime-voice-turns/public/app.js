const startButton = document.querySelector("#startButton");
const stopButton = document.querySelector("#stopButton");
const connectionStatus = document.querySelector("#connectionStatus");
const turnStatus = document.querySelector("#turnStatus");
const transcriptLog = document.querySelector("#transcriptLog");
const micRing = document.querySelector("#micRing");
const caseStrip = document.querySelector("#caseStrip");

let peerConnection = null;
let dataChannel = null;
let mediaStream = null;
let activeCase = null;
let messages = [];
let savedMessageCount = 0;
let processedToolCallIds = new Set();

function setStatus(status, detail) {
  connectionStatus.textContent = status;
  turnStatus.textContent = detail;
}

function setMode(mode) {
  document.body.dataset.mode = mode;
}

function appendLog(label, text) {
  const muted = transcriptLog.querySelector(".muted");
  if (muted) muted.remove();

  const row = document.createElement("p");
  const speaker = document.createElement("strong");
  speaker.textContent = label;
  row.append(speaker, ` ${text}`);
  transcriptLog.append(row);
  transcriptLog.scrollTop = transcriptLog.scrollHeight;
}

function recordMessage(speaker, transcript) {
  const cleanTranscript = transcript?.trim();
  if (!cleanTranscript) return;

  const last = messages.at(-1);
  if (last?.speaker === speaker && last?.transcript === cleanTranscript) return;

  messages.push({ speaker, transcript: cleanTranscript });
  appendLog(speaker, cleanTranscript);
}

async function saveNewMessages() {
  const unsavedMessages = messages.slice(savedMessageCount);
  if (!activeCase || unsavedMessages.length === 0) return;

  const response = await fetch("/conversation-log", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      caseData: activeCase,
      messages: unsavedMessages
    })
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  const data = await response.json();
  savedMessageCount = messages.length;
  appendLog("system", `Saved ${data.rows_written} row(s) to data/output/conversations.csv.`);
}

function parseFunctionArguments(rawArguments) {
  if (!rawArguments) return {};

  if (typeof rawArguments === "object") {
    return rawArguments;
  }

  try {
    return JSON.parse(rawArguments);
  } catch {
    return {
      transcript_summary: String(rawArguments),
      stated_reason: String(rawArguments),
      parent_confirmed: false,
      language: activeCase?.guardian_language ?? "English",
      absence_dates: activeCase?.absent_date ? [activeCase.absent_date] : []
    };
  }
}

async function submitAttendanceExcuse(functionCall) {
  const toolCallId = functionCall.call_id;
  if (!toolCallId || processedToolCallIds.has(toolCallId)) return;

  processedToolCallIds.add(toolCallId);
  const excuse = parseFunctionArguments(functionCall.arguments);
  appendLog("system", "Submitting confirmed excuse to the mock attendance datastore.");

  const response = await fetch("/attendance-excuse", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      caseData: activeCase,
      excuse
    })
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  const result = await response.json();
  appendLog("system", `Excuse saved as ${result.excuse_record_id} (${result.status}).`);

  dataChannel.send(JSON.stringify({
    type: "conversation.item.create",
    item: {
      type: "function_call_output",
      call_id: toolCallId,
      output: JSON.stringify(result)
    }
  }));

  dataChannel.send(JSON.stringify({
    type: "response.create",
    response: {
      output_modalities: ["audio"],
      instructions:
        "Tell the parent the attendance office has recorded the explanation for review. Keep it brief and use the conversation language."
    }
  }));
}

function handleFunctionCalls(response) {
  const functionCalls = (response?.output ?? []).filter((item) => item.type === "function_call");
  let handled = false;

  for (const functionCall of functionCalls) {
    if (functionCall.name !== "submit_attendance_excuse") continue;
    handled = true;
    setMode("thinking");
    setStatus("Saving Excuse", "Submitting the confirmed parent response.");
    submitAttendanceExcuse(functionCall).catch((error) => {
      setMode("error");
      setStatus("Save Error", "The attendance excuse could not be saved.");
      appendLog("error", error instanceof Error ? error.message : "Unknown save error.");
    });
  }

  return handled;
}

function getOutputTranscript(item) {
  return (item.content ?? [])
    .map((part) => part.transcript ?? part.text ?? "")
    .filter(Boolean)
    .join(" ");
}

function handleRealtimeEvent(rawEvent) {
  const event = JSON.parse(rawEvent.data);

  switch (event.type) {
    case "session.created":
      setStatus("Connected", "Listening. Starting the attendance call.");
      appendLog("system", "Realtime session created.");
      break;
    case "input_audio_buffer.speech_started":
      setMode("listening");
      setStatus("Listening", "I hear you. Finish your thought, then pause.");
      break;
    case "input_audio_buffer.speech_stopped":
      setMode("thinking");
      setStatus("Thinking", "End of turn detected. Waiting for the response.");
      break;
    case "response.created":
      setMode("responding");
      setStatus("Responding", "The computer is answering.");
      break;
    case "response.output_audio_transcript.done":
      recordMessage("assistant", event.transcript);
      break;
    case "conversation.item.done":
      if (event.item?.role === "user") {
        const text = getOutputTranscript(event.item);
        recordMessage("parent", text);
      }
      break;
    case "response.done":
      if (!handleFunctionCalls(event.response)) {
        setMode("ready");
        setStatus("Listening", "Ready for the parent response or next call turn.");
      }
      saveNewMessages().catch((error) => {
        setMode("error");
        setStatus("Save Error", "The conversation transcript could not be saved.");
        appendLog("error", error instanceof Error ? error.message : "Unknown save error.");
      });
      break;
    case "error":
      setMode("error");
      setStatus("Error", event.error?.message ?? "Realtime error.");
      appendLog("error", event.error?.message ?? JSON.stringify(event));
      break;
    default:
      break;
  }
}

async function loadCase() {
  const response = await fetch("/case");
  if (!response.ok) {
    throw new Error(await response.text());
  }

  activeCase = await response.json();
  caseStrip.textContent = `${activeCase.student_name} | ${activeCase.absences_this_year} absence(s) this year | Policy max ${activeCase.max_absences_per_school_year}`;
}

async function startSession() {
  startButton.disabled = true;
  setMode("connecting");
  setStatus("Connecting", "Requesting microphone access.");
  messages = [];
  savedMessageCount = 0;
  processedToolCallIds = new Set();
  await loadCase();

  peerConnection = new RTCPeerConnection();

  const audio = document.createElement("audio");
  audio.autoplay = true;
  peerConnection.ontrack = (event) => {
    audio.srcObject = event.streams[0];
  };

  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true
    }
  });
  mediaStream.getAudioTracks().forEach((track) => peerConnection.addTrack(track, mediaStream));

  dataChannel = peerConnection.createDataChannel("oai-events");
  dataChannel.addEventListener("message", handleRealtimeEvent);
  dataChannel.addEventListener("open", () => {
    setMode("ready");
    setStatus("Connected", "Starting the attendance notice.");
    dataChannel.send(JSON.stringify({
      type: "response.create",
      response: {
        output_modalities: ["audio"],
        instructions: "Begin the attendance call now. Use the configured attendance case and policy."
      }
    }));
  });

  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  const sdpResponse = await fetch("/session", {
    method: "POST",
    body: offer.sdp,
    headers: {
      "Content-Type": "application/sdp"
    }
  });

  if (!sdpResponse.ok) {
    const errorText = await sdpResponse.text();
    throw new Error(errorText || "Failed to create Realtime session");
  }

  await peerConnection.setRemoteDescription({
    type: "answer",
    sdp: await sdpResponse.text()
  });

  stopButton.disabled = false;
  micRing.setAttribute("aria-hidden", "true");
}

function stopSession() {
  mediaStream?.getTracks().forEach((track) => track.stop());
  dataChannel?.close();
  peerConnection?.close();

  mediaStream = null;
  dataChannel = null;
  peerConnection = null;

  startButton.disabled = false;
  stopButton.disabled = true;
  setMode("idle");
  setStatus("Idle", "Click Start, allow the mic, then respond as the parent.");
}

loadCase().catch((error) => {
  setMode("error");
  caseStrip.textContent = "Could not load attendance case.";
  appendLog("error", error instanceof Error ? error.message : "Unknown case load error.");
});

startButton.addEventListener("click", async () => {
  try {
    await startSession();
  } catch (error) {
    stopSession();
    setMode("error");
    setStatus("Error", error instanceof Error ? error.message : "Could not start session.");
  }
});

stopButton.addEventListener("click", stopSession);
