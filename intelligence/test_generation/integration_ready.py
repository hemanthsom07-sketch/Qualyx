"""
Integration-Ready Result (Task 9)
====================================

Task 9's goal is to make Intelligence's output ready for the next
integration stage: something a caller (eventually Backend) can send
straight to the Execution Engine, while still keeping full provenance
available for storage/display/diagnosis.

Today, getting both pieces requires calling the pipeline twice:
    generated = generate_test_from_real_recorder_events(...)   # provenance
    payload   = generate_execution_payload_from_real_recorder_events(...)  # wire shape
which silently repeats the same understand_journey()/generate_test()
work twice and risks the two results drifting apart if called at
different times.

IntegrationReadyResult bundles both from a single generation pass:
    - generated_test: the full LocalGeneratedTest (stable IDs,
      source_event_id/source_step_id provenance, and
      ungeneratable_steps with reasons -- nothing here is dropped)
    - execution_payload: the exact wire-shape dict already established
      in Task 8 ({"journeyId": ..., "steps": [{"id": ..., "type": ...}]})

This module adds no new classification/generation logic of its own --
it is pure composition over the existing, unmodified engines.
"""

from dataclasses import dataclass

from .generated_test import LocalGeneratedTest
from .execution_payload import to_execution_test_payload


@dataclass
class IntegrationReadyResult:
    """Bundles the provenance-rich generated test with its execution-ready payload."""
    generated_test: LocalGeneratedTest
    execution_payload: dict


def build_integration_ready_result(generated_test: LocalGeneratedTest) -> IntegrationReadyResult:
    """
    Derives the execution_payload from an already-produced generated_test
    (via the existing, unmodified to_execution_test_payload) and returns
    both together. Does not recompute or alter generated_test in any way.
    """
    return IntegrationReadyResult(
        generated_test=generated_test,
        execution_payload=to_execution_test_payload(generated_test),
    )
