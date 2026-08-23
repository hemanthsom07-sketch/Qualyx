import type { Diagnosis } from "../api/types";

interface DiagnosisCardProps {
  diagnosis: Diagnosis;
}

// Lower-level, raw diagnosis view (see backend/app/schemas/diagnosis.py:
// DiagnosisOut, a field-for-field mirror of Intelligence's
// FailureDiagnosisResult). Deliberately kept separate from
// ExplanationCard, which is the human-readable summary -- this card is
// the "why the system believes this classification" detail view.
export function DiagnosisCard({ diagnosis }: DiagnosisCardProps) {
  if (!diagnosis.has_failure) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400">
        No failure diagnosed.
      </div>
    );
  }

  return (
    <div data-testid="diagnosis-card" className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm">
      <h4 className="font-medium text-slate-100 mb-2">Diagnosis</h4>
      <dl className="space-y-1">
        {diagnosis.classification && (
          <Row label="Classification" value={diagnosis.classification} />
        )}
        <Row label="Confidence" value={diagnosis.confidence.toFixed(2)} />
        <Row
          label="Correlation established"
          value={diagnosis.correlation_established ? "Yes" : "No"}
        />
        {diagnosis.failed_step_id && <Row label="Failed step" value={diagnosis.failed_step_id} />}
        {diagnosis.generated_step_id && (
          <Row label="Generated step" value={diagnosis.generated_step_id} />
        )}
        {diagnosis.source_step_id && <Row label="Source step" value={diagnosis.source_step_id} />}
        {diagnosis.source_event_id && (
          <Row label="Source event" value={diagnosis.source_event_id} />
        )}
        {diagnosis.error && <Row label="Error" value={diagnosis.error} />}
      </dl>

      {diagnosis.explanation && (
        <p className="mt-3 text-slate-300">{diagnosis.explanation}</p>
      )}

      {diagnosis.evidence.length > 0 && (
        <ul className="mt-2 list-disc list-inside text-slate-400 space-y-0.5">
          {diagnosis.evidence.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="text-slate-500 shrink-0">{label}:</dt>
      <dd className="text-slate-300 break-words">{value}</dd>
    </div>
  );
}
