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

Neither entry point adds new classification or generation logic --
they are pure composition/translation on top of the already-tested
Task 3/4 engines.

Redaction handling: if the Recorder has already redacted a sensitive
input value (value=None, redacted=True in the real contract), this
pipeline does not attempt to recover, alter, or re-derive the original
value, and does not fabricate a placeholder string. The step is
reported as ungeneratable with an explicit redaction reason instead.
Intelligence never sees or handles raw passwords; that responsibility
belongs to the Recorder.
"""

from .journey_understanding import understand_journey
from .journey_understanding.local_fixtures import LocalRawJourney
from .journey_understanding.recorder_adapter import RealRecordedEvent, adapt_real_journey
from .test_generation import generate_test
from .test_generation.generated_test import LocalGeneratedTest


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
