// Qualyx Recorder — content script.
//
// Captures only: page load, button clicks, link clicks, and text
// input/change events. Reports every event to the background service
// worker, which decides (based on current recording status) whether to
// keep it. Does not decide recording state itself, and does not
// implement selector ranking, DOM snapshotting, or screenshots.

import {
  buildClickEvent,
  buildInputChangeEvent,
  buildPageLoadEvent,
  findClickableAncestor,
  isRecordableFormField
} from "./lib/eventCapture";
import type { RecordedEvent } from "./lib/eventCapture";

function report(event: RecordedEvent) {
  chrome.runtime.sendMessage({ type: "RECORD_EVENT", event });
}

// Page load / navigation: a content script re-runs on every full
// navigation and every reload, so reporting once on injection covers
// "page navigation/page load" for this foundation milestone.
report(buildPageLoadEvent(location.href));

document.addEventListener(
  "click",
  (e) => {
    const clickable = findClickableAncestor(e.target as Element | null);
    if (!clickable) return;
    report(buildClickEvent(clickable, location.href));
  },
  true
);

document.addEventListener(
  "change",
  (e) => {
    const target = e.target as Element | null;
    if (!isRecordableFormField(target)) return;
    report(buildInputChangeEvent(target, location.href));
  },
  true
);
