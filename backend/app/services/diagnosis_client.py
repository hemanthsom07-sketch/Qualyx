"""
Backend <-> Intelligence boundary (Milestone 2A).

Unlike execution_client.py's subprocess boundary to the Execution Engine
(a separate Node process), Intelligence is a pure, dependency-free Python
package with no conflicting requirements, so this boundary is a direct
in-process import rather than a subprocess call. No new process, no new
serialization protocol -- just translation between Backend's existing
Pydantic models and Intelligence's existing dataclasses.

This module contains NO diagnosis logic and NO explainability logic of
its own. It only:
  1. Makes the sibling `intelligence` package importable (see path setup
     below -- mirrors execution_client.py's own pattern of resolving a
     sibling directory under the repo root).
  2. Translates ExecutionResultOut -> intelligence.diagnosis.ExecutionResult
     (field-for-field, same names -- both mirror the same underlying
     Execution Engine contract).
  3. Translates a stored TestDefinition's `content` list into
     intelligence.test_generation.LocalGeneratedTest, the shape
     diagnose_execution_result() requires.
  4. Calls the existing, unmodified diagnose_execution_result() and
     explain_diagnosis() functions and returns their results as-is.

Provenance discipline (per Milestone 2A design decision):
The stored TestDefinition.content (whether created via
create_test_definition() or from-execution-payload) never contains
source_step_id/source_event_id -- confirmed absent from both ingestion
schemas. LocalGeneratedStep.source_step_id is declared as a required
`str` in Intelligence's dataclass, but Python dataclasses do not enforce
type hints at runtime, so this module deliberately passes None for both
source_step_id and source_event_id rather than fabricating a value (e.g.
reusing step_id as a stand-in). This correctly surfaces as `null` in the
FailureDiagnosisResult/API response instead of a misleading fabricated
value -- consistent with the explicit "never fabricate provenance"
requirement. This is flagged here, not hidden, because it depends on a
detail (unenforced dataclass typing) of Intelligence's implementation
that Backend does not own.

Only content items that have a stored `id` are translated into a
LocalGeneratedStep at all. Items without a stored id are skipped rather
than assigned a synthetic id: such steps could never have been sent to
the Execution Engine with an id either, so the engine could never echo
a matching failedStepId back for them -- they are structurally
uncorrelatable regardless, and giving them a synthetic local id would
imply a provenance/identity that was never actually generated.
"""

import sys
from pathlib import Path

# Intelligence is a sibling package under the repo root
# (backend/ and intelligence/ are siblings), not a subpackage of
# Backend's own `app`, so it is not on sys.path by default. This
# mirrors execution_client.py's own _resolve_execution_engine_dir():
# this file is backend/app/services/diagnosis_client.py, so
# parents[2] resolves to backend/, and its parent is the repo root.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from intelligence.diagnosis import (  # noqa: E402
    ExecutionResult as IntelExecutionResult,
    StepExecutionResult as IntelStepExecutionResult,
    FailureDiagnosisResult,
    diagnose_execution_result,
)
from intelligence.explainability import explain_diagnosis, ExplainedDiagnosis  # noqa: E402
from intelligence.test_generation.generated_test import (  # noqa: E402
    LocalGeneratedStep,
    LocalGeneratedTest,
)

from app.schemas.execution import ExecutionResultOut


def _to_intelligence_execution_result(result: ExecutionResultOut) -> IntelExecutionResult:
    """
    Field-for-field translation. Both ExecutionResultOut (Backend) and
    IntelExecutionResult (Intelligence) mirror the same real Execution
    Engine contract (execution-engine/src/types.ts), so no values are
    invented or reinterpreted here.
    """
    return IntelExecutionResult(
        status=result.status,
        failedStepIndex=result.failed_step_index,
        failedStepId=result.failed_step_id,
        error=result.error,
        executedStepCount=result.executed_step_count,
        steps=[
            IntelStepExecutionResult(id=s.id, status=s.status, error=s.error)
            for s in result.steps
        ],
        startedAt=result.started_at,
        finishedAt=result.finished_at,
        durationMs=result.duration_ms,
    )


def _generated_test_from_stored_content(
    test_definition_id: str, content: list[dict]
) -> LocalGeneratedTest:
    """
    Builds the LocalGeneratedTest representation diagnose_execution_result()
    requires, from a stored TestDefinition's `content`. See module
    docstring for the provenance and id-skipping rules this follows.

    `journey_id` uses the real, stored TestDefinition id -- not a
    fabricated value -- since LocalGeneratedTest requires some
    identifier and this field is never inspected by diagnosis logic
    itself (only .steps is).
    """
    steps: list[LocalGeneratedStep] = []
    for item in content:
        step_id = item.get("id")
        if not step_id:
            # No stored id: this step could never have been correlated
            # via failedStepId in the first place. Skip rather than
            # fabricate an id for it.
            continue
        steps.append(
            LocalGeneratedStep(
                step_id=step_id,
                kind=item.get("type"),
                source_step_id=None,  # never fabricated -- see module docstring
                source_event_id=None,  # never fabricated -- see module docstring
                url=item.get("url"),
                selector=item.get("selector"),
                selector_kind=item.get("selectorKind"),
                value=item.get("value"),
                # Phase 4 selector-evidence milestone: read back the raw
                # secondary-identifier evidence stored alongside the
                # primary selector, same pattern as selector_kind above.
                # item.get() returns None for older stored content that
                # predates this milestone -- never fabricated.
                element_id=item.get("stableElementId"),
                data_testid=item.get("stableDataTestId"),
            )
        )
    return LocalGeneratedTest(journey_id=test_definition_id, steps=steps)


def diagnose_and_explain(
    test_definition_id: str,
    content: list[dict],
    execution_result: ExecutionResultOut,
) -> tuple[FailureDiagnosisResult, ExplainedDiagnosis]:
    """
    The single entry point the execution route calls. Composes the
    existing, unmodified diagnose_execution_result() and
    explain_diagnosis() -- no classification or presentation logic
    lives in this module.
    """
    generated_test = _generated_test_from_stored_content(test_definition_id, content)
    intel_execution_result = _to_intelligence_execution_result(execution_result)
    diagnosis = diagnose_execution_result(generated_test, intel_execution_result)
    explanation = explain_diagnosis(diagnosis)
    return diagnosis, explanation
