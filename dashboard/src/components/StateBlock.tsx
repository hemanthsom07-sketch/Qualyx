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
interface StateBlockProps {
  children: React.ReactNode;
  tone?: "neutral" | "error";
}

export function StateBlock({ children, tone = "neutral" }: StateBlockProps) {
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
      {children}
    </div>
  );
}
