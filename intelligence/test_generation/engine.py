"""
Deterministic Test Generation Prototype
=========================================

Milestone scope (Task 4): convert a normalized journey (from
journey_understanding) into a minimal, deterministic browser-test
representation. No LLM. No Playwright framework generation. No
execution.

Supported generated step kinds:
- navigate (from STEP_NAVIGATE)
- click    (from STEP_CLICK)
- fill     (from STEP_FILL)

Selector policy: prefer stable selectors only.
  1. data-testid, if present
  2. element id, if present
  3. otherwise: do NOT guess. Record the step as ungeneratable with a
     reason, and do not emit a generated step for it.

This module does not modify or depend on Claude 2's execution engine.
It only produces a representation that could conceptually be consumed
by it later, once a real shared contract exists.
"""

from ..journey_understanding.normalized_journey import (
    LocalNormalizedJourney,
    LocalJourneyUnderstandingStep,
    STEP_NAVIGATE,
    STEP_CLICK,
    STEP_FILL,
)
from .generated_test import (
    LocalGeneratedTest,
    LocalGeneratedStep,
    LocalUngeneratableStep,
    GEN_STEP_NAVIGATE,
    GEN_STEP_CLICK,
    GEN_STEP_FILL,
)


def _resolve_stable_selector(step: LocalJourneyUnderstandingStep):
    """
    Returns (selector, selector_kind) if a stable selector is available,
    otherwise (None, None). Only data-testid and element id are
    considered stable for this milestone -- no CSS-selector guessing,
    no text-based selector fabrication.
    """
    if step.element is None:
        return None, None
    if step.element.data_testid:
        return f'[data-testid="{step.element.data_testid}"]', "data-testid"
    if step.element.element_id:
        return f"#{step.element.element_id}", "id"
    return None, None


def generate_test(normalized_journey: LocalNormalizedJourney) -> LocalGeneratedTest:
    """
    Deterministically generate a minimal test representation from a
    normalized journey. Step order is preserved. Steps lacking enough
    safe information are reported as ungeneratable rather than guessed.
    """
    generated_steps: list[LocalGeneratedStep] = []
    ungeneratable_steps: list[LocalUngeneratableStep] = []

    for step in normalized_journey.steps:
        if step.kind == STEP_NAVIGATE:
            if not step.url:
                ungeneratable_steps.append(
                    LocalUngeneratableStep(
                        source_step_id=step.step_id,
                        reason="Navigate step has no URL to navigate to.",
                    )
                )
                continue
            generated_steps.append(
                LocalGeneratedStep(
                    step_id=f"gen-{step.step_id}",
                    kind=GEN_STEP_NAVIGATE,
                    source_step_id=step.step_id,
                    url=step.url,
                )
            )

        elif step.kind == STEP_CLICK:
            selector, selector_kind = _resolve_stable_selector(step)
            if selector is None:
                ungeneratable_steps.append(
                    LocalUngeneratableStep(
                        source_step_id=step.step_id,
                        reason=(
                            "Click step has no stable selector "
                            "(no data-testid or element id available); "
                            "refusing to guess a selector."
                        ),
                    )
                )
                continue
            generated_steps.append(
                LocalGeneratedStep(
                    step_id=f"gen-{step.step_id}",
                    kind=GEN_STEP_CLICK,
                    source_step_id=step.step_id,
                    selector=selector,
                    selector_kind=selector_kind,
                )
            )

        elif step.kind == STEP_FILL:
            selector, selector_kind = _resolve_stable_selector(step)
            if selector is None:
                ungeneratable_steps.append(
                    LocalUngeneratableStep(
                        source_step_id=step.step_id,
                        reason=(
                            "Fill step has no stable selector "
                            "(no data-testid or element id available); "
                            "refusing to guess a selector."
                        ),
                    )
                )
                continue
            if step.value is None:
                if step.redacted:
                    ungeneratable_steps.append(
                        LocalUngeneratableStep(
                            source_step_id=step.step_id,
                            reason=(
                                "Fill step has a stable selector, but the Recorder "
                                "redacted this input's value. Intelligence never "
                                "fabricates or reconstructs redacted values, so this "
                                "step cannot be safely generated."
                            ),
                        )
                    )
                else:
                    ungeneratable_steps.append(
                        LocalUngeneratableStep(
                            source_step_id=step.step_id,
                            reason="Fill step has a stable selector but no value to fill.",
                        )
                    )
                continue
            generated_steps.append(
                LocalGeneratedStep(
                    step_id=f"gen-{step.step_id}",
                    kind=GEN_STEP_FILL,
                    source_step_id=step.step_id,
                    selector=selector,
                    selector_kind=selector_kind,
                    value=step.value,
                )
            )

        else:
            # Should not happen given journey_understanding's supported
            # kinds, but handled safely rather than assumed.
            ungeneratable_steps.append(
                LocalUngeneratableStep(
                    source_step_id=step.step_id,
                    reason=f"Unsupported normalized step kind: {step.kind}",
                )
            )

    return LocalGeneratedTest(
        journey_id=normalized_journey.journey_id,
        steps=generated_steps,
        ungeneratable_steps=ungeneratable_steps,
    )
