// Qualyx Recorder — popup controls.
// Start / Stop / Clear recording, plus live status and event count.
// Talks only to the background service worker via runtime messages;
// does not touch chrome.storage directly to avoid duplicating the
// single source of truth that lives in background.ts.

interface StateResponse {
  status: "idle" | "recording" | "stopped";
  count: number;
}

const statusEl = document.getElementById("status") as HTMLElement;
const countEl = document.getElementById("count") as HTMLElement;
const startBtn = document.getElementById("start-btn") as HTMLButtonElement;
const stopBtn = document.getElementById("stop-btn") as HTMLButtonElement;
const clearBtn = document.getElementById("clear-btn") as HTMLButtonElement;

function render(state: StateResponse) {
  statusEl.textContent = state.status;
  countEl.textContent = String(state.count);
  startBtn.disabled = state.status === "recording";
  stopBtn.disabled = state.status !== "recording";
}

function refresh() {
  chrome.runtime.sendMessage({ type: "GET_STATE" }, (response: StateResponse) => {
    if (response) render(response);
  });
}

startBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "START_RECORDING" }, (response: StateResponse) => {
    if (response) render(response);
  });
});

stopBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "STOP_RECORDING" }, (response: StateResponse) => {
    if (response) render(response);
  });
});

clearBtn.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "CLEAR_RECORDING" }, (response: StateResponse) => {
    if (response) render(response);
  });
});

refresh();
