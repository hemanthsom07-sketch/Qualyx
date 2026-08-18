// Focused tests for eventCapture.ts's stable-identifier capture logic.
//
// No prior test file/tooling existed for the Recorder package before
// this milestone (confirmed by audit) -- this adds the minimal test
// runner setup (node:test + tsx), mirroring execution-engine's own
// already-established pattern (see execution-engine/package.json's
// "test" script), rather than introducing new tooling.
//
// A minimal fake Element is used since these are pure functions that
// only call getAttribute()/tagName/textContent/.value -- no real DOM
// or jsdom dependency is needed to exercise them.

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  getStableIdentifier,
  getStableIdentifiers,
  buildClickEvent,
  buildInputChangeEvent
} from "../src/lib/eventCapture.js";

function fakeElement(attrs: Record<string, string>, opts: { tagName?: string; text?: string; value?: string } = {}) {
  return {
    getAttribute: (name: string) => (name in attrs ? attrs[name] : null),
    tagName: opts.tagName ?? "BUTTON",
    textContent: opts.text ?? "",
    value: opts.value ?? ""
  } as unknown as Element;
}

// --- getStableIdentifier(): existing behavior, must remain unchanged ---

test("getStableIdentifier prefers id when both id and data-testid exist (unchanged legacy behavior)", () => {
  const el = fakeElement({ id: "checkout-button", "data-testid": "checkout-submit" });
  assert.equal(getStableIdentifier(el), "checkout-button");
});

test("getStableIdentifier falls back to data-testid when id is absent (unchanged legacy behavior)", () => {
  const el = fakeElement({ "data-testid": "checkout-submit" });
  assert.equal(getStableIdentifier(el), "data-testid:checkout-submit");
});

test("getStableIdentifier returns undefined when neither is present (unchanged legacy behavior)", () => {
  const el = fakeElement({});
  assert.equal(getStableIdentifier(el), undefined);
});

// --- getStableIdentifiers(): new, non-collapsing dual capture ---

test("getStableIdentifiers captures BOTH id and data-testid when both genuinely exist", () => {
  const el = fakeElement({ id: "checkout-button", "data-testid": "checkout-submit" });
  const result = getStableIdentifiers(el);
  assert.equal(result.htmlId, "checkout-button");
  assert.equal(result.dataTestId, "checkout-submit");
});

test("getStableIdentifiers captures only id when data-testid is absent", () => {
  const el = fakeElement({ id: "checkout-button" });
  const result = getStableIdentifiers(el);
  assert.equal(result.htmlId, "checkout-button");
  assert.equal(result.dataTestId, undefined);
});

test("getStableIdentifiers captures only data-testid when id is absent", () => {
  const el = fakeElement({ "data-testid": "checkout-submit" });
  const result = getStableIdentifiers(el);
  assert.equal(result.htmlId, undefined);
  assert.equal(result.dataTestId, "checkout-submit");
});

test("getStableIdentifiers fabricates neither when neither attribute exists", () => {
  const el = fakeElement({});
  const result = getStableIdentifiers(el);
  assert.equal(result.htmlId, undefined);
  assert.equal(result.dataTestId, undefined);
});

test("getStableIdentifiers never derives one identifier's value from the other", () => {
  // Distinct values -- if one were ever accidentally derived from the
  // other, this would catch it.
  const el = fakeElement({ id: "id-value-abc", "data-testid": "testid-value-xyz" });
  const result = getStableIdentifiers(el);
  assert.equal(result.htmlId, "id-value-abc");
  assert.equal(result.dataTestId, "testid-value-xyz");
  assert.notEqual(result.htmlId, result.dataTestId);
});

// --- buildClickEvent / buildInputChangeEvent: full event shape ---

test("buildClickEvent includes both new evidence fields alongside the unchanged elementId", () => {
  const el = fakeElement(
    { id: "checkout-button", "data-testid": "checkout-submit" },
    { tagName: "BUTTON", text: "Checkout" }
  );
  const event = buildClickEvent(el, "https://shop.test/");

  assert.equal(event.elementId, "checkout-button"); // unchanged legacy field
  assert.equal(event.elementHtmlId, "checkout-button");
  assert.equal(event.elementDataTestId, "checkout-submit");
  assert.equal(event.elementText, "Checkout");
});

test("buildClickEvent with only id present: new fields reflect only real evidence", () => {
  const el = fakeElement({ id: "checkout-button" }, { tagName: "BUTTON" });
  const event = buildClickEvent(el, "https://shop.test/");

  assert.equal(event.elementHtmlId, "checkout-button");
  assert.equal(event.elementDataTestId, undefined);
});

test("buildClickEvent with neither present: no evidence fabricated", () => {
  const el = fakeElement({}, { tagName: "DIV" });
  const event = buildClickEvent(el, "https://shop.test/");

  assert.equal(event.elementId, undefined);
  assert.equal(event.elementHtmlId, undefined);
  assert.equal(event.elementDataTestId, undefined);
});

test("buildInputChangeEvent preserves both identifiers for a non-sensitive field", () => {
  const el = fakeElement(
    { id: "search-box", "data-testid": "search-input" },
    { tagName: "INPUT", value: "running shoes" }
  );
  const event = buildInputChangeEvent(el, "https://shop.test/search");

  assert.equal(event.elementHtmlId, "search-box");
  assert.equal(event.elementDataTestId, "search-input");
  assert.equal(event.value, "running shoes");
  assert.equal(event.redacted, undefined);
});

test("buildInputChangeEvent for a redacted sensitive field still preserves selector evidence, never the value", () => {
  const el = fakeElement(
    { id: "card-number", "data-testid": "card-number-input", type: "password" },
    { tagName: "INPUT", value: "4111111111111111" }
  );
  const event = buildInputChangeEvent(el, "https://shop.test/checkout");

  assert.equal(event.redacted, true);
  assert.equal(event.value, undefined);
  // Selector evidence is independent of the sensitive VALUE and must
  // still be captured -- knowing "there is a stable selector for this
  // field" is not sensitive; the field's contents are.
  assert.equal(event.elementHtmlId, "card-number");
  assert.equal(event.elementDataTestId, "card-number-input");
  // Never leaked into any evidence field.
  const serialized = JSON.stringify(event);
  assert.ok(!serialized.includes("4111111111111111"));
});
