// Qualyx Recorder — shared local state shape + storage key.
// Local to the extension only, not a cross-module contract.

import type { RecordedEvent } from "./eventCapture";

export type RecordingStatus = "idle" | "recording" | "stopped";

export interface RecorderState {
  status: RecordingStatus;
  events: RecordedEvent[];
}

export const STORAGE_KEY = "qualyx_recorder_state";

export const DEFAULT_STATE: RecorderState = {
  status: "idle",
  events: []
};
