import type { Explanation } from "../api/types";

interface ExplanationCardProps {
  explanation: Explanation;
}

// The primary, human-readable "what happened / why" summary (see
// backend/app/schemas/diagnosis.py: ExplanationOut, mirroring
// Intelligence's ExplainedDiagnosis). Meant to be the first thing a
// normal Dashboard user reads -- DiagnosisCard is the lower-level
// detail underneath it.
export function ExplanationCard({ explanation }: ExplanationCardProps) {
  return (
    <div
      data-testid="explanation-card"
      className="rounded-lg border border-slate-800 bg-slate-900/50 p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-medium text-slate-100">{explanation.headline}</h3>
        {explanation.has_failure && (
          <span className="shrink-0 text-xs font-medium text-slate-500 uppercase tracking-wide">
            {explanation.confidence_level} confidence
          </span>
        )}
      </div>

      {explanation.explanation && (
        <p className="mt-2 text-sm text-slate-300">{explanation.explanation}</p>
      )}

      {explanation.evidence.length > 0 && (
        <ul className="mt-3 list-disc list-inside text-sm text-slate-400 space-y-0.5">
          {explanation.evidence.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
