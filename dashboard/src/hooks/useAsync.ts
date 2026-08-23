import { useEffect, useState } from "react";

// Small generic hook so ProjectsPage/ProjectDetailPage/TestDetailPage
// don't each hand-roll the same loading/error/data state machine. This
// is the only new abstraction introduced in Stage 2 — deliberately kept
// tiny (no caching, no retries, no global store) rather than reaching
// for a data-fetching library.

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

/**
 * Runs `fetcher` whenever any value in `deps` changes, tracking
 * loading/error/success state. `fetcher` is expected to reject with an
 * Error (ApiError from ../api/client qualifies) whose `message` is
 * already a safe, user-facing string -- this hook never exposes a raw
 * stack trace, only `error.message`.
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: "success", data });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : "Something went wrong.";
        setState({ status: "error", message });
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
