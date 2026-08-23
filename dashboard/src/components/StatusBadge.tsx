import type { StatusTone } from "../lib/status";

interface StatusBadgeProps {
  label: string;
  tone: StatusTone;
}

const TONE_CLASSES: Record<StatusTone, string> = {
  pass: "bg-emerald-950 text-emerald-400 border-emerald-800",
  fail: "bg-red-950 text-red-400 border-red-800",
  neutral: "bg-slate-800 text-slate-300 border-slate-700",
};

// Always renders the status as text, not just a color swatch -- a
// colorblind user or a screenshot without color still reads "FAIL"/
// "PASS"/etc. directly.
export function StatusBadge({ label, tone }: StatusBadgeProps) {
  return (
    <span
      className={`inline-block rounded-md border px-2 py-0.5 text-xs font-semibold tracking-wide ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}
