import type { FailureEvidence } from "../api/types";

interface FailureEvidenceCardProps {
  evidence: FailureEvidence;
}

// Every field here is genuinely optional in the Backend schema (see
// backend/app/schemas/execution.py: FailureEvidenceOut / 
// FailureEvidenceActionOut's "absent unless present" serializer) --
// this component mirrors that by only rendering rows whose value
// actually exists, rather than showing "N/A"/blank placeholders.
//
// Stage 18: `action.url`/`pageUrl` are real URLs the failure happened
// at/against, but were previously shown as inert text -- a user
// investigating a failure had no way to actually go look at the page.
// They're now clickable (opening in a new tab), which is the one
// concrete "next action" this evidence can actually support without
// inventing a recovery capability the backend doesn't provide.
export function FailureEvidenceCard({ evidence }: FailureEvidenceCardProps) {
  const rows: { label: string; value: string; href?: string }[] = [];

  rows.push({ label: "Error", value: evidence.errorMessage });
  rows.push({ label: "Category", value: evidence.errorCategory });
  if (evidence.action.url) {
    rows.push({ label: "URL", value: evidence.action.url, href: evidence.action.url });
  }
  if (evidence.action.selector) rows.push({ label: "Selector", value: evidence.action.selector });
  if (evidence.pageUrl) {
    rows.push({ label: "Page URL", value: evidence.pageUrl, href: evidence.pageUrl });
  }
  if (evidence.httpStatus !== null) {
    rows.push({ label: "HTTP status", value: String(evidence.httpStatus) });
  }

  return (
    <div
      data-testid="failure-evidence"
      className="rounded-lg border border-red-900/60 bg-red-950/20 p-4 text-sm"
    >
      <h4 className="font-medium text-red-400 mb-2">Failure evidence</h4>
      <dl className="space-y-1">
        {rows.map((row) => (
          <div key={row.label} className="flex gap-2">
            <dt className="text-slate-500 shrink-0">{row.label}:</dt>
            <dd className="text-slate-300 break-words">
              {row.href ? (
                <a
                  href={row.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 rounded"
                >
                  {row.value}
                </a>
              ) : (
                row.value
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
