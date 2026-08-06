// Qualyx Recorder — background service worker.
//
// Single source of truth for recording status + captured events, held in
// chrome.storage.local (so navigating/reloading the Demo App doesn't lose
// the current session). Content scripts always report events; this
// service worker decides whether to keep them, based on current status.
//
// Does NOT talk to any Backend, does NOT implement journey understanding,
// does NOT generate tests, does NOT take screenshots. Foundation only.

import { STORAGE_KEY, DEFAULT_STATE } from "./lib/state.js";
import type { RecorderState } from "./lib/state";
import type { RecordedEvent } from "./lib/eventCapture";

async function getState(): Promise<RecorderState> {
  const stored = await chrome.storage.local.get(STORAGE_KEY);
  return (stored[STORAGE_KEY] as RecorderState | undefined) ?? DEFAULT_STATE;
}

async function setState(state: RecorderState): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEY]: state });
}

chrome.runtime.onInstalled.addListener(async () => {
  const existing = await chrome.storage.local.get(STORAGE_KEY);
  if (!existing[STORAGE_KEY]) {
    await setState(DEFAULT_STATE);
  }
  console.log("[Qualyx Recorder] background service worker ready.");
});

type RuntimeMessage =
  | { type: "START_RECORDING" }
  | { type: "STOP_RECORDING" }
  | { type: "CLEAR_RECORDING" }
  | { type: "GET_STATE" }
  | { type: "RECORD_EVENT"; event: RecordedEvent };

chrome.runtime.onMessage.addListener((message: RuntimeMessage, _sender: unknown, sendResponse: (response?: unknown) => void) => {
  handleMessage(message).then(sendResponse);
  // Keep the message channel open for the async response above.
  return true;
});

async function handleMessage(message: RuntimeMessage) {
  const state = await getState();

  switch (message.type) {
    case "START_RECORDING": {
      const next: RecorderState = { ...state, status: "recording" };
      await setState(next);
      return { status: next.status, count: next.events.length };
    }

    case "STOP_RECORDING": {
      const next: RecorderState = { ...state, status: "stopped" };
      await setState(next);
      return { status: next.status, count: next.events.length };
    }

    case "CLEAR_RECORDING": {
      const next: RecorderState = { status: "idle", events: [] };
      await setState(next);
      return { status: next.status, count: next.events.length };
    }

    case "RECORD_EVENT": {
      if (state.status !== "recording") {
        return { status: state.status, count: state.events.length };
      }
      const next: RecorderState = { ...state, events: [...state.events, message.event] };
      await setState(next);
      return { status: next.status, count: next.events.length };
    }

    case "GET_STATE":
    default: {
      return { status: state.status, count: state.events.length };
    }
  }
}
