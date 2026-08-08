"""
Recorded Events -> Generated Test Pipeline (Task 5, corrected)
=================================================================

Two entry points are provided:

1. generate_test_from_recorded_events(raw_journey)
   Takes the prototype-local LocalRawJourney/LocalRawEvent shape
   (kept for continuity with Task 4's own tests) and composes:
       understand_journey() -> generate_test()

2. generate_test_from_real_recorder_events(journey_id, events)
   Takes the ACTUAL Recorder event contract, as inspected in
   recorder/src/lib/eventCapture.ts, translates it via
   journey_understanding.recorder_adapter, then runs the same
   understand_journey() -> generate_test() pipeline. This is the
   entry point intended for real integration.

3. generate_execution_payload_from_real_recorder_events(journey_id, events)
   (Task 8) Same as #2, but additionally serializes the result into
   the exact JSON shape Claude 2's Execution Engine expects:
   {"steps": [{"id": ..., "type": ..., ...}]}. Added for Task 8;
   composes existing, unmodified logic plus the new
   test_generation.execution_payload serializer -- no new ID scheme.

4. prepare_integration_ready_test_from_real_recorder_events(journey_id, events)
   (Task 9) The entry point intended for the next integration stage.
   Runs generation exactly once and returns BOTH the provenance-rich
   LocalGeneratedTest (stable IDs, source_event_id/source_step_id,
   ungeneratable_steps with reasons) and the execution-ready payload,
   bundled in an IntegrationReadyResult, so a caller doesn't have to
   invoke the pipeline twice (and risk the two results drifting apart)
   to get both views of the same generation pass.

5. diagnose_execution(generated_test_or_integration_result, execution_result)
   (Task 10) Accepts either a LocalGeneratedTest or an
   IntegrationReadyResult (unwrapped automatically) plus Claude 2's
   real ExecutionResult, and returns a FailureDiagnosisResult.
   Composes the existing, unmodified diagnosis.diagnose_execution_result()
   -- no new correlation or classification logic lives in pipeline.py
   itself.

None of these entry points adds new classification or generation
logic -- they are pure composition/translation on top of the
already-tested Task 3/4/7/8/10 engines.

Redaction handling: if the Recorder has already redacted a sensitive
input value (value=None, redacted=True in the real contract), this
pipeline does not attempt to recover, alter, or re-derive the original
value, and does not fabricate a placeholder string. The step is
reported as ungeneratable with an explicit redaction reason instead.
Intelligence never sees or handles raw passwords; that responsibility
belongs to the Recorder.
"""

from typing import Union

from .journey_understanding import understand_journey
from .journey_understanding.local_fixtures import LocalRawJourney
from .journey_understanding.recorder_adapter import RealRecordedEvent, adapt_real_journey
from .test_generation import generate_test
from .test_generation.generated_test import LocalGeneratedTest
from .test_generation.execution_payload import to_execution_test_payload
from .test_generation.integration_ready import IntegrationReadyResult, build_integration_ready_result
from .diagnosis.execution_result import ExecutionResult
from .diagnosis.failure_diagnosis import FailureDiagnosisResult, diagnose_execution_result


def generate_test_from_recorded_events(raw_journey: LocalRawJourney) -> LocalGeneratedTest:
    """
    Full pipeline entry point: recorded events (prototype/local shape)
    -> normalized journey -> generated test. Order-preserving,
    deterministic, no LLM calls.

    This is a pure composition of the two already-tested Task 4 stages;
    it adds no new classification/generation logic of its own.
    """
    normalized_journey = understand_journey(raw_journey)
    generated_test = generate_test(normalized_journey)
    return generated_test


def generate_test_from_real_recorder_events(
    journey_id: str, events: list[RealRecordedEvent]
) -> LocalGeneratedTest:
    """
    Full pipeline entry point using the ACTUAL Recorder event contract
    (recorder/src/lib/eventCapture.ts), inspected and confirmed in
    Task 5's correction:

        RealRecordedEvent (Recorder's real shape)
            -> adapt_real_journey()      [translation only, no logic]
            -> understand_journey()      [existing, unmodified engine]
            -> generate_test()           [existing engine, only the
                                           redacted-fill reason text
                                           was refined]

    This is the entry point Backend should call once real integration
    exists. It performs no guessing: missing stable selectors and
    redacted/missing input values are reported as ungeneratable steps
    rather than fabricated.
    """
    raw_journey = adapt_real_journey(journey_id, events)
    normalized_journey = understand_journey(raw_journey)
    generated = generate_test(normalized_journey)
    return generated


def generate_execution_payload_from_real_recorder_events(
    journey_id: str, events: list[RealRecordedEvent]
) -> dict:
    """
    (Task 8) Full pipeline entry point that returns the exact JSON
    payload shape Claude 2's Execution Engine expects:

        {"journeyId": ..., "steps": [{"id": ..., "type": ..., ...}]}

    Composes the unmodified generate_test_from_real_recorder_events()
    pipeline with to_execution_test_payload() for serialization only.
    "id" on each step is the same deterministic Task 7 step_id -- no
    new identifier is generated here.
    """
    generated = generate_test_from_real_recorder_events(journey_id, events)
    return to_execution_test_payload(generated)


def prepare_integration_ready_test_from_real_recorder_events(
    journey_id: str, events: list[RealRecordedEvent]
) -> IntegrationReadyResult:
    """
    (Task 9) Runs the real-Recorder pipeline exactly once and returns
    both the provenance-rich LocalGeneratedTest and its execution-ready
    payload together, via IntegrationReadyResult. This is the entry
    point intended for the next integration stage: a caller can send
    result.execution_payload straight to the Execution Engine while
    still having result.generated_test available for storage, display
    of ungeneratable_steps, or future diagnosis correlation -- without
    generating the test twice.
    """
    generated = generate_test_from_real_recorder_events(journey_id, events)
    return build_integration_ready_result(generated)


def diagnose_execution(
    generated_test_or_integration_result: Union[LocalGeneratedTest, IntegrationReadyResult],
    execution_result: ExecutionResult,
) -> FailureDiagnosisResult:
    """
    (Task 10) Diagnosis entry point for the real pipeline. Accepts
    either a LocalGeneratedTest directly, or an IntegrationReadyResult
    (its .generated_test is unwrapped automatically), plus Claude 2's
    real ExecutionResult, and returns a FailureDiagnosisResult.

    This is a thin composition over diagnosis.diagnose_execution_result()
    -- no correlation or classification logic is duplicated here.
    """
    if isinstance(generated_test_or_integration_result, IntegrationReadyResult):
        generated_test = generated_test_or_integration_result.generated_test
    else:
        generated_test = generated_test_or_integration_result

    return diagnose_execution_result(generated_test, execution_result)
