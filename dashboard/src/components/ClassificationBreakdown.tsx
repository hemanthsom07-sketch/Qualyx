interface ClassificationBreakdownProps {
  /** diagnosis_classification_counts, already confirmed non-empty by the caller. */
  counts: Record<string, number>;
}

// Renders exactly the keys/counts the backend returned -- no invented
// categories, no assumed ordering beyond "largest first" for
// readability. Bars are plain Tailwind width percentages, no charting
// library.
export function ClassificationBreakdown({ counts }: ClassificationBreakdownProps) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, count]) => count));

  return (
    <div data-testid="classification-breakdown" className="space-y-2">
      {entries.map(([classification, count]) => (
        <div key={classification} className="text-sm">
          <div className="flex items-center justify-between text-slate-300">
            <span>{classification}</span>
            <span className="text-slate-400">{count}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-800">
            <div
              className="h-2 rounded-full bg-slate-500"
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
