const startButton = document.querySelector("#startButton");
const hallPassButton = document.querySelector("#hallPassButton");
const resetButton = document.querySelector("#resetButton");
const micToggleButton = document.querySelector("#micToggleButton");
const callButtonLabel = document.querySelector("#callButtonLabel");
const hallPassButtonLabel = document.querySelector("#hallPassButtonLabel");
const micToggleLabel = document.querySelector("#micToggleLabel");
const connectionStatus = document.querySelector("#connectionStatus");
const turnStatus = document.querySelector("#turnStatus");
const transcriptLog = document.querySelector("#transcriptLog");
const micRing = document.querySelector("#micRing");
const caseStrip = document.querySelector("#caseStrip");
const callTab = document.querySelector("#callTab");
const systemTab = document.querySelector("#systemTab");
const callView = document.querySelector("#callView");
const systemView = document.querySelector("#systemView");
const themeToggle = document.querySelector("#themeToggle");
const localServerOrigin = "http://localhost:5178";

let peerConnection = null;
let dataChannel = null;
let mediaStream = null;
let activeCase = null;
let messages = [];
let savedMessageCount = 0;
let processedToolCallIds = new Set();
let isListenOnlySession = false;
let shouldKeepListenOnlyStatus = false;
let isMicrophoneListening = false;
let activeScenario = "absentee";
let isCaseSummaryVisible = false;

function apiPath(path) {
  if (window.location.protocol === "file:") {
    return `${localServerOrigin}${path}`;
  }

  return path;
}

const callScenarios = {
  absentee: {
    idleLabel: "Start Absentee Call",
    caseSummary: (caseData) => `${caseData.student_name} | ${caseData.absences_this_year} absence(s) this year | Policy max ${caseData.max_absences_per_school_year}`,
    issueSentence: (caseData) => `${caseData?.student_name ?? "The student"} was absent today. Please tell me, is there a valid reason for the absence?`
  },
  hallPass: {
    idleLabel: "Start Hall Pass Call",
    caseSummary: (caseData) => `${caseData.student_name} | 14 hall passes in 10 school days | 4 hours outside class`,
    issueSentence: (caseData) => `${caseData?.student_name ?? "The student"} has had 14 hall passes in the last 10 school days for a total of 4 hours of time outside class. Please tell me, is there a valid reason for this hall pass use?`
  }
};

function buildInitialCallInstructions(scenario = activeScenario) {
  const guardianName = activeCase?.parent_name ?? "the parent or guardian";
  const preferredLanguage = activeCase?.guardian_language ?? "unknown";
  const scenarioConfig = callScenarios[scenario] ?? callScenarios.absentee;
  const issueSentence = scenarioConfig.issueSentence(activeCase);

  return [
    "Start the call from the beginning now.",
    `This is the ${scenario} scenario. The issue sentence below is the only issue for this call.`,
    "Do not substitute a different attendance issue.",
    `First say exactly: "Hello this is Abe calling from the Austin High School. Is this ${guardianName}?"`,
    "Then immediately repeat the same opening statement in Spanish.",
    `The datastore preferred language is ${preferredLanguage}; use it only as a tie-breaker for ambiguous one-word replies.`,
    'If the guardian says "yes", continue in English. If the guardian says "sí" or "si", continue in Spanish. If the guardian only says "no", use the datastore preferred language as the language tie-breaker while handling the negative answer appropriately.',
    'If you still cannot tell the preferred language, ask once: "Would you prefer English or Spanish? ¿Prefiere inglés o español?"',
    "After the person confirms they are the guardian, continue in the selected language.",
    `Then say exactly: "${issueSentence}"`
  ].join(" ");
}

function setStatus(status, detail) {
  connectionStatus.textContent = status;
  turnStatus.textContent = detail;
}

function setMode(mode) {
  document.body.dataset.mode = mode;
}

function activateTab(tabName) {
  const isSystem = tabName === "system";

  callTab.classList.toggle("is-active", !isSystem);
  systemTab.classList.toggle("is-active", isSystem);
  callTab.setAttribute("aria-selected", String(!isSystem));
  systemTab.setAttribute("aria-selected", String(isSystem));
  callView.classList.toggle("is-active", !isSystem);
  systemView.classList.toggle("is-active", isSystem);
  callView.hidden = isSystem;
  systemView.hidden = !isSystem;
  const nextUrl = new URL(window.location.href);
  nextUrl.hash = isSystem ? "system" : "";
  window.history.replaceState(null, "", nextUrl);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const isDark = theme === "dark";
  themeToggle.textContent = isDark ? "Dark" : "Light";
  themeToggle.setAttribute("aria-pressed", String(isDark));
  localStorage.setItem("attendanceOfficerTheme", theme);
}

function toggleTheme() {
  const current = document.documentElement.dataset.theme ?? "light";
  applyTheme(current === "dark" ? "light" : "dark");
}

function setMicrophoneListening(enabled) {
  isMicrophoneListening = enabled;

  for (const track of mediaStream?.getAudioTracks() ?? []) {
    track.enabled = enabled;
  }

  micToggleLabel.textContent = enabled ? "Pause Mic" : "Enable Mic";
  micToggleButton.setAttribute("aria-pressed", String(enabled));
}

function resetMicrophoneToggle() {
  setMicrophoneListening(false);
  micToggleButton.disabled = true;
}

function setCallButtonStarted(started, scenario = activeScenario) {
  const absenteeStarted = started && scenario === "absentee";
  const hallPassStarted = started && scenario === "hallPass";

  callButtonLabel.textContent = absenteeStarted ? "End Call" : callScenarios.absentee.idleLabel;
  hallPassButtonLabel.textContent = hallPassStarted ? "End Call" : callScenarios.hallPass.idleLabel;
  startButton.classList.toggle("is-ending", absenteeStarted);
  hallPassButton.classList.toggle("is-ending", hallPassStarted);
  startButton.setAttribute("aria-pressed", String(absenteeStarted));
  hallPassButton.setAttribute("aria-pressed", String(hallPassStarted));
  startButton.disabled = started && !absenteeStarted;
  hallPassButton.disabled = started && !hallPassStarted;
}

function toggleMicrophoneListening() {
  if (!mediaStream || isListenOnlySession) return;

  const nextState = !isMicrophoneListening;
  setMicrophoneListening(nextState);
  setStatus(
    nextState ? "Mic Listening" : "Mic Paused",
    nextState ? "The parent microphone is on." : "The parent microphone is muted."
  );
}

function transcriptLabelFor(label) {
  const labels = {
    assistant: "ABE",
    parent: "GUARDIAN",
    system: "STATUS",
    error: "ERROR"
  };

  return labels[label] ?? label.toUpperCase();
}

function appendLog(label, text) {
  const muted = transcriptLog.querySelector(".muted");
  if (muted) muted.remove();

  const row = document.createElement("p");
  const speaker = document.createElement("strong");
  speaker.textContent = transcriptLabelFor(label);
  row.append(speaker, ` ${text}`);
  transcriptLog.append(row);
  transcriptLog.scrollTop = transcriptLog.scrollHeight;
}

function resetTranscriptLog() {
  transcriptLog.replaceChildren();
  const row = document.createElement("p");
  row.className = "muted";
  row.textContent = "Realtime events will appear here once connected.";
  transcriptLog.append(row);
}

function isMicrophonePermissionError(error) {
  return error instanceof DOMException && (
    error.name === "NotAllowedError" ||
    error.name === "PermissionDeniedError" ||
    error.name === "SecurityError"
  );
}

function showListenOnlyWarning() {
  shouldKeepListenOnlyStatus = true;
  setStatus("Microphone Blocked", "Starting listen-only preview. Use a browser with mic access to answer as the parent.");
  appendLog("system", "Microphone permission was denied, so this session will play the agent audio only.");
}

function startListenOnlySession() {
  isListenOnlySession = true;
  peerConnection.addTransceiver("audio", { direction: "recvonly" });
  showListenOnlyWarning();
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

  const response = await fetch(apiPath("/conversation-log"), {
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

  await response.json();
  savedMessageCount = messages.length;
  appendLog("system", "Data Saved.");
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

  const response = await fetch(apiPath("/attendance-excuse"), {
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
  appendLog("system", "Data Saved.");

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
      appendLog("error", "Data could not be saved.");
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
      if (!shouldKeepListenOnlyStatus) {
        setStatus("Connected", "Mic paused. Click Enable Mic when the parent is ready to respond.");
      }
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
        if (shouldKeepListenOnlyStatus) {
          setStatus("Listen Only", "Opening played. Parent responses need microphone access.");
        } else if (!isMicrophoneListening) {
          setStatus("Mic Paused", "Click Enable Mic when the parent is ready to respond.");
        } else {
          setStatus("Listening", "Ready for the parent response or next call turn.");
        }
      }
      saveNewMessages().catch((error) => {
        setMode("error");
        setStatus("Save Error", "The conversation transcript could not be saved.");
        appendLog("error", "Data could not be saved.");
      });
      break;
    case "error":
      setMode("error");
      setStatus("Error", event.error?.message ?? "Realtime error.");
      appendLog("error", "Realtime error.");
      break;
    default:
      break;
  }
}

async function loadCase() {
  const response = await fetch(apiPath("/case"));
  if (!response.ok) {
    throw new Error(await response.text());
  }

  activeCase = await response.json();
  renderCaseSummary(activeScenario);
}

function renderCaseSummary(scenario = activeScenario) {
  if (!activeCase || !isCaseSummaryVisible) return;

  const scenarioConfig = callScenarios[scenario] ?? callScenarios.absentee;
  caseStrip.textContent = scenarioConfig.caseSummary(activeCase);
  caseStrip.hidden = false;
}

function hideCaseSummary() {
  isCaseSummaryVisible = false;
  caseStrip.textContent = "";
  caseStrip.hidden = true;
}

async function startSession(scenario = "absentee") {
  activeScenario = scenario;
  isCaseSummaryVisible = true;
  renderCaseSummary(scenario);
  startButton.disabled = true;
  hallPassButton.disabled = true;
  resetButton.disabled = true;
  setMode("connecting");
  setStatus("Connecting", "Requesting microphone access.");
  messages = [];
  savedMessageCount = 0;
  processedToolCallIds = new Set();
  isListenOnlySession = false;
  shouldKeepListenOnlyStatus = false;
  resetTranscriptLog();
  await loadCase();

  peerConnection = new RTCPeerConnection();

  const audio = document.createElement("audio");
  audio.autoplay = true;
  peerConnection.ontrack = (event) => {
    audio.srcObject = event.streams[0];
  };

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    mediaStream.getAudioTracks().forEach((track) => peerConnection.addTrack(track, mediaStream));
    setMicrophoneListening(false);
  } catch (error) {
    if (!isMicrophonePermissionError(error)) {
      throw error;
    }

    startListenOnlySession();
  }

  dataChannel = peerConnection.createDataChannel("oai-events");
  dataChannel.addEventListener("message", handleRealtimeEvent);
  dataChannel.addEventListener("open", () => {
    setMode("ready");
    if (isListenOnlySession) {
      shouldKeepListenOnlyStatus = true;
      setStatus("Listen Only", "Playing the opening. Parent responses are disabled until microphone access is allowed.");
    } else {
      setStatus("Connected", "Starting the attendance notice. Mic is paused.");
    }
    dataChannel.send(JSON.stringify({
      type: "response.create",
      response: {
        output_modalities: ["audio"],
        instructions: buildInitialCallInstructions(scenario)
      }
    }));
  });

  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  const sdpResponse = await fetch(apiPath("/session"), {
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

  startButton.disabled = false;
  hallPassButton.disabled = false;
  setCallButtonStarted(true, scenario);
  resetButton.disabled = false;
  micToggleButton.disabled = isListenOnlySession;
  micRing.setAttribute("aria-hidden", "true");
}

function stopSession() {
  resetMicrophoneToggle();
  mediaStream?.getTracks().forEach((track) => track.stop());
  dataChannel?.close();
  peerConnection?.close();

  mediaStream = null;
  dataChannel = null;
  peerConnection = null;
  isListenOnlySession = false;
  shouldKeepListenOnlyStatus = false;

  startButton.disabled = false;
  hallPassButton.disabled = false;
  setCallButtonStarted(false);
  resetButton.disabled = true;
  setMode("idle");
  setStatus("Idle", "Click Start, allow the mic, then respond as the parent.");
  hideCaseSummary();
}

async function restartSession() {
  const scenario = activeScenario;
  resetButton.disabled = true;
  stopSession();
  await startSession(scenario);
}

loadCase().catch((error) => {
  setMode("error");
  isCaseSummaryVisible = true;
  caseStrip.textContent = "Could not load attendance case.";
  caseStrip.hidden = false;
  appendLog("error", "Could not load attendance case.");
});

async function handleScenarioButtonClick(scenario) {
  if (peerConnection) {
    stopSession();
    return;
  }

  try {
    await startSession(scenario);
  } catch (error) {
    stopSession();
    setMode("error");
    setStatus("Error", error instanceof Error ? error.message : "Could not start session.");
  }
}

startButton.addEventListener("click", () => {
  handleScenarioButtonClick("absentee");
});

hallPassButton.addEventListener("click", () => {
  handleScenarioButtonClick("hallPass");
});

micToggleButton.addEventListener("click", toggleMicrophoneListening);
resetButton.addEventListener("click", async () => {
  try {
    await restartSession();
  } catch (error) {
    stopSession();
    setMode("error");
    setStatus("Error", error instanceof Error ? error.message : "Could not reset session.");
  }
});

callTab.addEventListener("click", () => activateTab("call"));
systemTab.addEventListener("click", () => activateTab("system"));
themeToggle.addEventListener("click", toggleTheme);

applyTheme(localStorage.getItem("attendanceOfficerTheme") ?? "light");
if (window.location.hash === "#system") {
  activateTab("system");
}
