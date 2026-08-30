import { useState } from "react";

import { ApiError, createProject } from "../api/client";

interface CreateProjectFormProps {
  /** Controlled from the parent so multiple entry points (header action,
   *  empty-state CTA) can open the same form instance instead of each
   *  needing their own. */
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  /** Called after a project is successfully created, so the caller can refresh its list. */
  onCreated: () => void;
}

// Backend contract (backend/app/schemas/project.py: ProjectCreate):
// name required (1-255 chars), description optional (up to 2000 chars).
// This form mirrors exactly that -- no extra fields invented.
//
// Stage 14: open/closed state moved from internal to a controlled prop
// so ProjectsPage's empty-state "+ Create project" CTA can open this
// same form rather than needing a second, duplicate form.
export function CreateProjectForm({ isOpen, onOpenChange, onCreated }: CreateProjectFormProps) {
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
      onOpenChange(false);
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
        onClick={() => onOpenChange(true)}
        data-testid="new-project-button"
        className="shrink-0 rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
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

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button
          type="submit"
          disabled={submitting || !name.trim()}
          data-testid="create-project-submit"
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
        >
          {submitting ? "Creating…" : "Create project"}
        </button>
        <button
          type="button"
          onClick={() => {
            onOpenChange(false);
            setError(null);
          }}
          disabled={submitting}
          className="rounded-md px-4 py-2 text-sm text-slate-400 hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
