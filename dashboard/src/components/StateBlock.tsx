// Shared loading/error/empty state block. Reuses the existing dashed
// empty-state convention from RecordedSessions.tsx / PlaceholderPage.tsx
// rather than inventing a new visual pattern.

interface StateBlockProps {
  children: React.ReactNode;
  tone?: "neutral" | "error";
}

export function StateBlock({ children, tone = "neutral" }: StateBlockProps) {
  return (
    <div
      data-testid="state-block"
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
