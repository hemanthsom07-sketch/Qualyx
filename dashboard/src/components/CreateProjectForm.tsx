import { useState } from "react";

import { ApiError, createProject } from "../api/client";

interface CreateProjectFormProps {
  /** Called after a project is successfully created, so the caller can refresh its list. */
  onCreated: () => void;
}

// Backend contract (backend/app/schemas/project.py: ProjectCreate):
// name required (1-255 chars), description optional (up to 2000 chars).
// This form mirrors exactly that -- no extra fields invented.
export function CreateProjectForm({ onCreated }: CreateProjectFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName || submitting) return;

    setSubmitting(true);
    setError(null);
    try {
      await createProject({
        name: trimmedName,
        description: description.trim() || null,
      });
      setName("");
      setDescription("");
      setIsOpen(false);
      onCreated();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Couldn't create the project.";
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
        data-testid="new-project-button"
        className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-slate-500 hover:text-slate-100"
      >
        + New project
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="create-project-form"
      className="rounded-lg border border-slate-800 bg-slate-900/50 p-4"
    >
      <div>
        <label htmlFor="project-name" className="block text-sm text-slate-400 mb-1">
          Name
        </label>
        <input
          id="project-name"
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
        <label htmlFor="project-description" className="block text-sm text-slate-400 mb-1">
          Description <span className="text-slate-600">(optional)</span>
        </label>
        <textarea
          id="project-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={2000}
          rows={2}
          className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-slate-500 focus:outline-none"
        />
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting || !name.trim()}
          data-testid="create-project-submit"
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          {submitting ? "Creating…" : "Create project"}
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
