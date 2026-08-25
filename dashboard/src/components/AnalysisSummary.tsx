import type { FlakyAnalysisResult } from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface AnalysisSummaryProps {
  analysis: FlakyAnalysisResult;
}

// Conclusion logic mirrors intelligence/flaky_analysis/engine.py
// exactly (see comments at each branch below) -- nothing here is
// invented; every branch corresponds to a real backend-guaranteed
// combination of insufficient_data/is_flaky/consistently_failing.
function conclusion(analysis: FlakyAnalysisResult): { label: string; tone: "pass" | "fail" | "neutral" } {
  // Engine guarantees is_flaky is always false when insufficient_data,
  // but consistently_failing can independently be true even with too
  // little data (e.g. the only 2 executions available both failed) --
  // insufficient_data still takes priority as the primary conclusion,
  // per Stage 5's explicit instruction not to label that case
  // "not flaky" or otherwise paper over the lack of data.
  if (analysis.insufficient_data) return { label: "INSUFFICIENT DATA", tone: "neutral" };
  if (analysis.is_flaky) return { label: "FLAKY", tone: "fail" };
  if (analysis.consistently_failing) return { label: "CONSISTENTLY FAILING", tone: "fail" };
  return { label: "NOT FLAKY", tone: "pass" };
}

export function AnalysisSummary({ analysis }: AnalysisSummaryProps) {
  const { label, tone } = conclusion(analysis);

  return (
    <div data-testid="analysis-summary" className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-medium text-slate-100">Flakiness conclusion</h3>
        <StatusBadge label={label} tone={tone} />
      </div>

      {analysis.is_flaky && analysis.flaky_reason && (
        <p className="mt-2 text-sm text-slate-300">{analysis.flaky_reason}</p>
      )}

      {analysis.insufficient_data && analysis.consistently_failing && (
        <p className="mt-2 text-sm text-slate-400">
          Every execution analyzed so far has failed, but there isn't yet enough history to
          confirm this is a consistent (not flaky) failure pattern.
        </p>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-slate-400 sm:grid-cols-4">
        <div>
          <dt className="text-slate-500">Analyzed</dt>
          <dd className="text-slate-300">
            {analysis.executions_analyzed} execution{analysis.executions_analyzed === 1 ? "" : "s"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Passed</dt>
          <dd className="text-slate-300">{analysis.passed_count}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Failed</dt>
          <dd className="text-slate-300">{analysis.failed_count}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Window</dt>
          <dd className="text-slate-300">{analysis.window_description}</dd>
        </div>
      </dl>

      {analysis.most_frequent_failing_step_id && (
        <p className="mt-3 text-sm text-slate-400">
          Most frequent failing step:{" "}
          <span className="text-slate-200">{analysis.most_frequent_failing_step_id}</span>
        </p>
      )}

      {analysis.healing_attempted_count > 0 && (
        <p className="mt-3 text-sm text-slate-500">
          Healing attempted {analysis.healing_attempted_count} time
          {analysis.healing_attempted_count === 1 ? "" : "s"} — succeeded{" "}
          {analysis.healing_succeeded_count}, failed {analysis.healing_failed_count}.
        </p>
      )}

      {analysis.evidence.length > 0 && (
        <ul className="mt-3 list-disc list-inside text-sm text-slate-400 space-y-0.5">
          {analysis.evidence.map((item, index) => (
            <li key={index}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
