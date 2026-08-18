// Qualyx Recorder — pure event-capture logic.
//
// Deliberately separated from chrome.* APIs so this file can be unit
// tested in any DOM environment (including a plain browser page in tests)
// without loading the extension itself. This is a LOCAL event shape for
// the Recorder only — it is NOT the final shared RecordedJourney contract,
// which must still be agreed with Claude 2 (Backend) and Claude 3
// (Intelligence) before anything is uploaded/persisted.

export type RecordedEventType = "page_load" | "click" | "input_change";

export interface RecordedEvent {
  id: string;
  type: RecordedEventType;
  timestamp: number;
  pageUrl: string;
  targetTag?: string;
  elementId?: string;
  // Phase 4 selector-evidence preservation: independently-captured raw
  // identifiers, additive to `elementId` above. `elementId` is left
  // completely unchanged (still the single, preference-collapsed
  // encoding existing consumers rely on) for backward compatibility --
  // these two new fields exist purely to stop discarding the
  // non-preferred identifier when an element genuinely has both.
  elementHtmlId?: string;
  elementDataTestId?: string;
  elementText?: string;
  value?: string;
  redacted?: boolean;
}

const MAX_TEXT_LENGTH = 120;

/**
 * Prefers a real `id` attribute, falls back to `data-testid`.
 * Returns undefined if neither stable identifier is present.
 *
 * UNCHANGED (Phase 4 selector-evidence milestone): this function and
 * the `elementId` field it populates keep their exact existing
 * behavior/encoding for backward compatibility. See
 * getStableIdentifiers() below for the additive, non-collapsing
 * capture used for the two new evidence fields.
 */
export function getStableIdentifier(el: Element): string | undefined {
  const id = el.getAttribute("id");
  if (id) return id;

  const testId = el.getAttribute("data-testid");
  if (testId) return `data-testid:${testId}`;

  return undefined;
}

/**
 * Independently captures BOTH stable identifiers, when genuinely
 * present on the element -- unlike getStableIdentifier(), this never
 * short-circuits, so an element with both a real `id` and a real
 * `data-testid` yields both values instead of only the preferred one.
 * Neither value is derived from the other; a value is included only
 * when the corresponding attribute is genuinely present on the
 * element -- never fabricated.
 */
export function getStableIdentifiers(el: Element): { htmlId?: string; dataTestId?: string } {
  const htmlId = el.getAttribute("id") || undefined;
  const dataTestId = el.getAttribute("data-testid") || undefined;
  return { htmlId, dataTestId };
}

export function getElementText(el: Element): string | undefined {
  const text = (el.textContent || "").trim().replace(/\s+/g, " ");
  if (!text) return undefined;
  return text.length > MAX_TEXT_LENGTH ? `${text.slice(0, MAX_TEXT_LENGTH)}…` : text;
}

/**
 * SECURITY: values from password fields (and common sensitive
 * autocomplete hints) must never be recorded in plain text.
 */
export function isSensitiveInput(el: Element): boolean {
  const type = (el.getAttribute("type") || "").toLowerCase();
  if (type === "password") return true;

  const autocomplete = (el.getAttribute("autocomplete") || "").toLowerCase();
  if (
    autocomplete === "current-password" ||
    autocomplete === "new-password" ||
    autocomplete.startsWith("cc-")
  ) {
    return true;
  }

  return false;
}

function makeId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `evt_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function buildPageLoadEvent(pageUrl: string): RecordedEvent {
  return {
    id: makeId(),
    type: "page_load",
    timestamp: Date.now(),
    pageUrl
  };
}

export function buildClickEvent(el: Element, pageUrl: string): RecordedEvent {
  const { htmlId, dataTestId } = getStableIdentifiers(el);
  return {
    id: makeId(),
    type: "click",
    timestamp: Date.now(),
    pageUrl,
    targetTag: el.tagName.toLowerCase(),
    elementId: getStableIdentifier(el),
    elementHtmlId: htmlId,
    elementDataTestId: dataTestId,
    elementText: getElementText(el)
  };
}

export function buildInputChangeEvent(el: Element, pageUrl: string): RecordedEvent {
  const sensitive = isSensitiveInput(el);
  const rawValue = (el as HTMLInputElement).value;
  const { htmlId, dataTestId } = getStableIdentifiers(el);

  return {
    id: makeId(),
    type: "input_change",
    timestamp: Date.now(),
    pageUrl,
    targetTag: el.tagName.toLowerCase(),
    elementId: getStableIdentifier(el),
    elementHtmlId: htmlId,
    elementDataTestId: dataTestId,
    value: sensitive ? undefined : rawValue,
    redacted: sensitive || undefined
  };
}

/** Finds the nearest ancestor (or self) button/link, or null if none. */
export function findClickableAncestor(el: Element | null): Element | null {
  return el ? el.closest("button, a") : null;
}

export function isRecordableFormField(el: Element | null): el is HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement {
  if (!el) return false;
  const tag = el.tagName.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select";
}
