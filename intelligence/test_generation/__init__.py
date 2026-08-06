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

__all__ = [
    "generate_test",
    "LocalGeneratedTest",
    "LocalGeneratedStep",
    "LocalUngeneratableStep",
    "GEN_STEP_NAVIGATE",
    "GEN_STEP_CLICK",
    "GEN_STEP_FILL",
]
