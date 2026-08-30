import { useState } from "react";

import { ApiError, createTestDefinition, type CreateTestStepInput } from "../api/client";

interface CreateTestFormProps {
  projectId: string;
  /** Called after a test is successfully created, so the caller can refresh its list. */
  onCreated: () => void;
}

type DraftStep =
  | { type: "navigate"; url: string }
  | { type: "click"; selector: string }
  | { type: "fill"; selector: string; value: string };

function emptyStep(type: DraftStep["type"]): DraftStep {
  if (type === "navigate") return { type: "navigate", url: "" };
  if (type === "click") return { type: "click", selector: "" };
  return { type: "fill", selector: "", value: "" };
}

// Backend contract (backend/app/schemas/test_definition.py):
// TestDefinitionCreate { name, description?, content: Step[] }, where
// Step is exactly navigate (url) | click (selector) | fill (selector,
// value). Only those three step shapes and fields are offered here --
// nothing from the schema's automated-ingestion fields (id,
// selectorKind, stableElementId, stableDataTestId) is exposed, since a
// human filling out this form has no meaningful value to put in them.
export function CreateTestForm({ projectId, onCreated }: CreateTestFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [steps, setSteps] = useState<DraftStep[]>([emptyStep("navigate")]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateStep(index: number, next: DraftStep) {
    setSteps((prev) => prev.map((step, i) => (i === index ? next : step)));
  }

  function removeStep(index: number) {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }

  function addStep() {
    setSteps((prev) => [...prev, emptyStep("navigate")]);
  }

  function reset() {
    setName("");
    setDescription("");
    setSteps([emptyStep("navigate")]);
    setError(null);
  }

  // Content must be non-empty (schema: Field(min_length=1)) and every
  // step's own required field(s) must be filled in -- checked here so
  // the submit button reflects real validity rather than letting a
  // guaranteed-422 request go out.
  const isValid =
    name.trim().length > 0 &&
    steps.length > 0 &&
    steps.every((step) =>
      step.type === "navigate" ? step.url.trim().length > 0 : step.selector.trim().length > 0
    );

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!isValid || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      const content: CreateTestStepInput[] = steps.map((step) =>
        step.type === "navigate"
          ? { type: "navigate", url: step.url.trim() }
          : step.type === "click"
            ? { type: "click", selector: step.selector.trim() }
            : { type: "fill", selector: step.selector.trim(), value: step.value }
      );
      await createTestDefinition(projectId, {
        name: name.trim(),
        description: description.trim() || null,
        content,
      });
      reset();
      setIsOpen(false);
      onCreated();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Couldn't create the test.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        data-testid="new-test-button"
        className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-slate-100"
      >
        + New test
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="create-test-form"
      className="rounded-lg border border-slate-800 bg-slate-900/50 p-4"
    >
      <div>
        <label htmlFor="test-name" className="block text-sm text-slate-400 mb-1">
          Name
        </label>
        <input
          id="test-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={255}
          required
          autoFocus
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        />
      </div>

      <div className="mt-3">
        <label htmlFor="test-description" className="block text-sm text-slate-400 mb-1">
          Description <span className="text-slate-600">(optional)</span>
        </label>
        <textarea
          id="test-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={2000}
          rows={2}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        />
      </div>

      <div className="mt-4">
        <span className="block text-sm text-slate-400 mb-2">Steps</span>
        <div className="space-y-2">
          {steps.map((step, index) => (
            <div
              key={index}
              className="flex items-start gap-2 rounded-md border border-slate-800 bg-slate-950 p-2"
            >
              <select
                aria-label={`Step ${index + 1} type`}
                value={step.type}
                onChange={(event) =>
                  updateStep(index, emptyStep(event.target.value as DraftStep["type"]))
                }
                className="shrink-0 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
              >
                <option value="navigate">navigate</option>
                <option value="click">click</option>
                <option value="fill">fill</option>
              </select>

              {step.type === "navigate" && (
                <input
                  type="text"
                  placeholder="URL"
                  aria-label={`Step ${index + 1} URL`}
                  value={step.url}
                  onChange={(event) => updateStep(index, { type: "navigate", url: event.target.value })}
                  className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
                />
              )}

              {step.type === "click" && (
                <input
                  type="text"
                  placeholder="Selector"
                  aria-label={`Step ${index + 1} selector`}
                  value={step.selector}
                  onChange={(event) =>
                    updateStep(index, { type: "click", selector: event.target.value })
                  }
                  className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
                />
              )}

              {step.type === "fill" && (
                <>
                  <input
                    type="text"
                    placeholder="Selector"
                    aria-label={`Step ${index + 1} selector`}
                    value={step.selector}
                    onChange={(event) =>
                      updateStep(index, { ...step, type: "fill", selector: event.target.value })
                    }
                    className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    placeholder="Value"
                    aria-label={`Step ${index + 1} value`}
                    value={step.value}
                    onChange={(event) =>
                      updateStep(index, { ...step, type: "fill", value: event.target.value })
                    }
                    className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200 focus:border-slate-500 focus:outline-none"
                  />
                </>
              )}

              <button
                type="button"
                onClick={() => removeStep(index)}
                disabled={steps.length === 1}
                aria-label={`Remove step ${index + 1}`}
                className="shrink-0 rounded-md px-2 py-1.5 text-sm text-slate-500 hover:text-red-400 disabled:cursor-not-allowed disabled:text-slate-700"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addStep}
          className="mt-2 text-sm text-slate-400 hover:text-slate-200"
        >
          + Add step
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting || !isValid}
          data-testid="create-test-submit"
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          {submitting ? "Creating…" : "Create test"}
        </button>
        <button
          type="button"
          onClick={() => {
            setIsOpen(false);
            setError(null);
          }}
          disabled={submitting}
          className="rounded-md px-4 py-2 text-sm text-slate-400 hover:text-slate-200"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
