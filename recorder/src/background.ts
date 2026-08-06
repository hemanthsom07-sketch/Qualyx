// Qualyx Recorder — background service worker (foundation only).
//
// This is intentionally a stub. It does NOT yet:
//   - implement the RecordedJourney contract
//   - communicate with the Backend
//   - manage recording session state
//
// It exists only to prove the extension's build and manifest wiring work.

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Qualyx Recorder] background service worker installed (foundation build).");
});
