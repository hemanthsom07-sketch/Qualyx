// Shared loading/error/empty state block. Reuses the existing dashed
// empty-state convention from RecordedSessions.tsx / PlaceholderPage.tsx
// rather than inventing a new visual pattern.
//
// Stage 13: every loading/error message in the Dashboard renders
// through this one component, but none of it was previously announced
// to assistive technology -- a screen reader user got no indication
// that an error (or a loading message replacing prior content)
// appeared. `role="alert"` (implicit aria-live="assertive") is used for
// errors since those need immediate attention; `role="status"`
// (implicit aria-live="polite") covers loading/empty/neutral content,
// which can wait until the user is idle.
//
// Stage 20: optional `onRetry` renders a Retry button for error states
// backed by useAsync's new retry() -- previously a failed fetch left
// the user stuck on this exact message with no in-page way to recover.
interface StateBlockProps {
  children: React.ReactNode;
  tone?: "neutral" | "error";
  onRetry?: () => void;
}

export function StateBlock({ children, tone = "neutral", onRetry }: StateBlockProps) {
  return (
    <div
      data-testid="state-block"
      role={tone === "error" ? "alert" : "status"}
      className={`border border-dashed rounded-lg p-8 text-center ${
        tone === "error"
          ? "border-red-900 text-red-400"
          : "border-slate-700 text-slate-400"
      }`}
    >
      <p>{children}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          data-testid="state-block-retry"
          className="mt-3 rounded-md border border-red-800 px-3 py-1.5 text-sm text-red-300 hover:border-red-600 hover:text-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
        >
          Retry
        </button>
      )}
    </div>
  );
}
