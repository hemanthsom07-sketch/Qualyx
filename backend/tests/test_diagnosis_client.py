"""
Direct unit tests for app.services.diagnosis_client's internal
stored-content -> LocalGeneratedTest reconstruction.

Unlike test_execution_diagnosis.py (which exercises this indirectly,
through the real POST /tests/{id}/execute HTTP path), these tests call
_generated_test_from_stored_content() directly, since it's the exact
function responsible for restoring Phase 4 selector-evidence fields
(stableElementId/stableDataTestId) from stored TestDefinition content
back into LocalGeneratedStep.element_id/data_testid -- the one place
"diagnosis reconstruction" (item 12 of the Phase 4 selector-evidence
audit) actually happens.
"""

from app.services.diagnosis_client import _generated_test_from_stored_content


def test_reconstruction_restores_dual_selector_evidence():
    content = [
        {"id": "gen-nav-1", "type": "navigate", "url": "https://shop.test/"},
        {
            "id": "gen-click-1",
            "type": "click",
            "selector": '[data-testid="checkout-submit"]',
            "selectorKind": "data-testid",
            "stableElementId": "checkout-button",
            "stableDataTestId": "checkout-submit",
        },
    ]

    generated_test = _generated_test_from_stored_content("test-def-1", content)

    click_step = generated_test.steps[1]
    assert click_step.selector == '[data-testid="checkout-submit"]'
    assert click_step.selector_kind == "data-testid"
    assert click_step.element_id == "checkout-button"
    assert click_step.data_testid == "checkout-submit"


def test_reconstruction_restores_single_identifier_without_fabricating_the_other():
    content = [
        {
            "id": "gen-click-1",
            "type": "click",
            "selector": "#checkout-button",
            "selectorKind": "id",
            "stableElementId": "checkout-button",
            # no stableDataTestId key at all
        },
    ]

    generated_test = _generated_test_from_stored_content("test-def-1", content)

    click_step = generated_test.steps[0]
    assert click_step.element_id == "checkout-button"
    assert click_step.data_testid is None  # never fabricated


def test_reconstruction_of_legacy_content_without_evidence_fields_is_unaffected():
    """
    Backward compatibility: TestDefinition content stored before the
    Phase 4 selector-evidence milestone has no stableElementId/
    stableDataTestId keys at all. Reconstruction must not fail or
    fabricate values for it -- both fields simply remain None, exactly
    as selector_kind already behaves for even older pre-Task-8 content.
    """
    content = [
        {"type": "navigate", "url": "https://shop.test/"},
        {"type": "click", "selector": "#legacy-button"},
    ]

    generated_test = _generated_test_from_stored_content("test-def-1", content)

    # Legacy navigate step has no "id" at all, so it's skipped per the
    # existing, unmodified id-skipping rule -- only the click step
    # remains, and it too has no "id", so it is ALSO skipped. Use
    # content with ids to actually observe the click step's fields.
    assert generated_test.steps == []


def test_reconstruction_of_legacy_content_with_id_but_no_evidence_fields():
    content = [
        {"id": "gen-click-1", "type": "click", "selector": "#legacy-button"},
    ]

    generated_test = _generated_test_from_stored_content("test-def-1", content)

    click_step = generated_test.steps[0]
    assert click_step.selector == "#legacy-button"
    assert click_step.element_id is None
    assert click_step.data_testid is None
