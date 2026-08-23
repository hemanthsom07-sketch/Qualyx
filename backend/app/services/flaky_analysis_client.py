"""
Backend <-> Intelligence flaky-analysis boundary (Phase 5 Stage 2).

Mirrors diagnosis_client.py's / healing_client.py's exact pattern:
Intelligence's flaky_analysis module is a plain, dependency-free Python
package living as a sibling directory, so this is an in-process
composition boundary, not a subprocess. The sys.path bootstrap below is
the same idempotent pattern those two modules already use -- repeated
here (not imported from either) so this module has no import-order
dependency on them having run first.

This module contains NO analysis logic of its own -- it only:
  1. Makes the sibling `intelligence` package importable.
  2. Translates real app.models.execution_run.ExecutionRun rows
     (queried newest-first, matching the existing
     GET /tests/{test_id}/executions convention) into
     intelligence.flaky_analysis.ExecutionRecord -- REVERSING the
     order to oldest-first, since ExecutionRecord's own docstring
     requires chronological order for its "pass between the earliest
     and latest occurrence of a signature" reasoning to be correct.
     Getting this reversal wrong would silently invert which
     occurrence is "first" vs "last" without causing any error --
     see the Stage 2 test suite's explicit ordering tests.
  3. Calls the existing, unmodified analyze_executions() -- Stage 1's
     analysis logic is not duplicated or reimplemented here.

diagnosis/healing are read from ExecutionRun's own JSON columns
exactly as persisted (see
app/api/routes/test_definitions.py's _persist_execution_run()) --
.get() is used defensively so a row predating Stage 2/3 (diagnosis/
healing still null) never raises, correctly yielding None rather than
fabricating a classification or healing status.
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from intelligence.flaky_analysis import (  # noqa: E402
    analyze_executions,
    ExecutionRecord,
    FlakyAnalysisResult,
)

from app.models.execution_run import ExecutionRun


def _to_execution_record(run: ExecutionRun) -> ExecutionRecord:
    """Translates one real ExecutionRun row into Intelligence's ExecutionRecord."""
    diagnosis = run.diagnosis or {}
    healing = run.healing or {}
    return ExecutionRecord(
        execution_id=run.id,
        status=run.status,
        failed_step_id=run.failed_step_id,
        diagnosis_classification=diagnosis.get("classification"),
        healing_status=healing.get("status"),
    )


def analyze_test_definition(
    test_definition_id: str,
    runs_newest_first: list[ExecutionRun],
) -> FlakyAnalysisResult:
    """
    `runs_newest_first` must already be ordered newest-first -- exactly
    what a DB query ordered by created_at.desc() (the existing
    GET /tests/{test_id}/executions convention) returns. This function
    reverses that ordering into oldest-first before calling the
    Intelligence engine, per ExecutionRecord's own contract.
    """
    chronological = list(reversed(runs_newest_first))
    records = [_to_execution_record(run) for run in chronological]
    return analyze_executions(test_definition_id, records)
