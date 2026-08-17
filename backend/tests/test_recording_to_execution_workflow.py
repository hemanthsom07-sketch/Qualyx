"""
End-to-end API-level integration test for the full backend workflow:

    Recorder events
    -> POST /projects/{project_id}/recordings
    -> generated TestDefinition
    -> POST /tests/{test_id}/execute
    -> execution result + diagnosis + explanation

Unlike test_recordings.py (which mocks Intelligence entirely, to unit-test
the recordings route's own wiring in isolation) and
test_execution_diagnosis.py (which starts from an already-created
TestDefinition), this test deliberately lets the REAL recording ->
Intelligence path run for real: real journey_understanding, real
test_generation, real diagnosis, real explainability. The only thing
mocked is execute_steps() -- the actual Execution Engine subprocess
boundary -- since that requires a live Node/Playwright process this
suite must not depend on. This mirrors the same boundary every other
Backend test in this suite already mocks (test_execution.py,
test_execution_diagnosis.py, test_recordings.py all mock execute_steps
the same way); nothing new is introduced here, only composed across two
existing endpoints in one test.

No internal Python function (build_execution_payload_from_events,
diagnose_and_explain, etc.) is called directly by this test -- every
step goes through the real HTTP API (POST .../recordings,
POST .../execute), per the requirement to prove the API-level chain,
not the internal wiring already covered by unit-level tests.
"""

from unittest.mock import patch

from app.schemas.execution import ExecutionResultOut

# A realistic Recorder payload: page load, a nav click, a legitimate
# text fill, a checkout click (which will be made to fail below), and a
# sensitive card-number input that Recorder redacted (value withheld,
# redacted=True). This mirrors the real RecordedEvent wire contract
# exactly (see app/schemas/recording.py).
RECORDER_PAYLOAD = {
    "journeyId": "journey-e2e-checkout",
    "events": [
        {
            "id": "evt-1",
            "type": "page_load",
            "timestamp": 1000.0,
            "pageUrl": "https://shop.example.com/",
        },
        {
            "id": "evt-2",
            "type": "click",
            "timestamp": 1200.0,
            "pageUrl": "https://shop.example.com/",
            "targetTag": "a",
            "elementId": "nav-search",
            "elementText": "Search",
        },
        {
            "id": "evt-3",
            "type": "input_change",
            "timestamp": 1400.0,
            "pageUrl": "https://shop.example.com/search",
            "targetTag": "input",
            "elementId": "search-box",
            "value": "running shoes",
        },
        {
            "id": "evt-4",
            "type": "click",
            "timestamp": 1600.0,
            "pageUrl": "https://shop.example.com/search",
            "targetTag": "button",
            "elementId": "checkout-submit",
            "elementText": "Checkout",
        },
        {
            "id": "evt-5",
            "type": "input_change",
            "timestamp": 1800.0,
            "pageUrl": "https://shop.example.com/checkout",
            "targetTag": "input",
            "elementId": "card-number",
            "value": None,
            "redacted": True,
        },
    ],
}


def _create_project(client, name="E2E Workflow Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_recording_to_execution_to_diagnosis_workflow(client):
    # --- Step 1: create the project ---
    project_id = _create_project(client)

    # --- Step 2: submit the Recorder payload; real Intelligence runs ---
    recording_response = client.post(
        f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD
    )
    assert recording_response.status_code == 201
    test_definition = recording_response.json()
    test_id = test_definition["id"]

    assert test_definition["name"] == "journey-e2e-checkout"

    content = test_definition["content"]
    # The redacted card-number input produced no fabricated fill step:
    # only the 4 genuinely generatable steps are present, never 5.
    assert len(content) == 4
    assert content[0] == {
        "id": "gen-step-evt-1",
        "type": "navigate",
        "url": "https://shop.example.com/",
    }
    assert content[1]["type"] == "click"
    assert content[1]["selector"] == "#nav-search"
    # The legitimate (non-redacted) fill value survived intact.
    assert content[2]["type"] == "fill"
    assert content[2]["selector"] == "#search-box"
    assert content[2]["value"] == "running shoes"
    assert content[3]["type"] == "click"
    assert content[3]["selector"] == "#checkout-submit"
    failed_step_id = content[3]["id"]  # gen-step-evt-4

    # No trace of the redacted event's sensitive field/value anywhere in
    # the stored TestDefinition response.
    recording_body_text = recording_response.text
    assert "card-number" not in recording_body_text
    assert "redacted" not in recording_body_text

    # --- Step 3: execute the generated test; only execute_steps is mocked ---
    execution_result = ExecutionResultOut.model_validate(
        {
            "status": "failed",
            "steps": [
                {"stepIndex": 0, "id": content[0]["id"], "type": "navigate", "status": "passed", "durationMs": 40},
                {"stepIndex": 1, "id": content[1]["id"], "type": "click", "status": "passed", "durationMs": 25},
                {"stepIndex": 2, "id": content[2]["id"], "type": "fill", "status": "passed", "durationMs": 15},
                {
                    "stepIndex": 3,
                    "id": failed_step_id,
                    "type": "click",
                    "status": "failed",
                    "durationMs": 5000,
                    "error": "Request failed with status code 503",
                },
            ],
            "failedStepIndex": 3,
            "failedStepId": failed_step_id,
            "error": "Request failed with status code 503",
            "executedStepCount": 4,
            "startedAt": "2026-01-01T00:00:00.000Z",
            "finishedAt": "2026-01-01T00:00:05.080Z",
            "durationMs": 5080,
            "evidence": {
                "failedStepId": failed_step_id,
                "failedStepIndex": 3,
                "stepType": "click",
                "action": {"selector": "#checkout-submit"},
                "errorMessage": "Request failed with status code 503",
                "errorCategory": "unknown",
                "pageUrl": "https://shop.example.com/search",
                "httpStatus": 503,
                "executedStepCount": 4,
                "stepDurationMs": 5000,
            },
        }
    )

    with patch(
        "app.api.routes.test_definitions.execute_steps", return_value=execution_result
    ) as mock_execute_steps:
        execute_response = client.post(f"/tests/{test_id}/execute")

    assert execute_response.status_code == 200

    # The exact generated steps (including the real fill value) reached
    # the execution boundary unmodified -- proving survival from
    # recording ingestion through to execution.
    called_steps = mock_execute_steps.call_args.args[0]
    assert called_steps == content
    assert called_steps[2]["value"] == "running shoes"

    body = execute_response.json()

    # --- execution result (existing fields, unchanged) ---
    assert body["status"] == "failed"
    assert body["failedStepId"] == failed_step_id
    assert body["failedStepIndex"] == 3
    assert body["evidence"]["errorCategory"] == "unknown"
    assert body["evidence"]["httpStatus"] == 503

    # --- diagnosis: real diagnose_execution_result() ran, not a mock ---
    diagnosis = body["diagnosis"]
    assert diagnosis["has_failure"] is True
    assert diagnosis["correlation_established"] is True
    assert diagnosis["generated_step_id"] == failed_step_id
    assert diagnosis["classification"] == "APPLICATION_BUG"
    # Provenance was never available from recording ingestion (Intelligence's
    # execution-payload contract deliberately doesn't carry
    # source_step_id/source_event_id through to stored TestDefinition
    # content) and must not be fabricated here either.
    assert diagnosis["source_step_id"] is None
    assert diagnosis["source_event_id"] is None

    # --- explanation: real explain_diagnosis() ran, not a mock ---
    explanation = body["explanation"]
    assert explanation["classification"] == "APPLICATION_BUG"
    assert explanation["headline"] == "Likely an application bug"
    assert explanation["confidence"] == diagnosis["confidence"]

    # --- no sensitive Recorder value fabricated or leaked anywhere in
    #     the full execution/diagnosis/explanation response ---
    execute_body_text = execute_response.text
    assert "card-number" not in execute_body_text
