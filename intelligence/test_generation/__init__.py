"""
Test Generation package — Task 4 milestone.

Contains a deterministic normalized-journey -> minimal-generated-test
transformation PROTOTYPE only. See engine.py for the generation logic
and generated_test.py for the temporary local output types.

This is NOT the final shared TestDefinition contract, and does not
implement or depend on Claude 2's execution engine.
"""

from .engine import generate_test
from .generated_test import (
    LocalGeneratedTest,
    LocalGeneratedStep,
    LocalUngeneratableStep,
    GEN_STEP_NAVIGATE,
    GEN_STEP_CLICK,
    GEN_STEP_FILL,
)
from .execution_payload import (
    to_execution_step_payload,
    to_execution_test_payload,
    find_generated_step_by_id,
)

__all__ = [
    "generate_test",
    "LocalGeneratedTest",
    "LocalGeneratedStep",
    "LocalUngeneratableStep",
    "GEN_STEP_NAVIGATE",
    "GEN_STEP_CLICK",
    "GEN_STEP_FILL",
    "to_execution_step_payload",
    "to_execution_test_payload",
    "find_generated_step_by_id",
]