"""
Tests for POST /projects/{project_id}/recordings.

This endpoint ingests raw Recorder events, runs them through
Intelligence's generate_execution_payload_from_real_recorder_events()
pipeline (via app/services/intelligence_client.py), and stores the
result as a TestDefinition — reusing the same ExecutionPayloadCreate
validation/storage logic as
POST /projects/{project_id}/tests/from-execution-payload.

app.api.routes.recordings.build_execution_payload_from_events is mocked
here rather than importing the real `intelligence` package, for the
same reason execute_steps() is mocked in tests/test_execution.py: this
keeps the Python test suite independently runnable without requiring
Intelligence's full dependency tree to be importable from the Backend's
test environment. The Backend<->Intelligence import boundary mechanism
itself (sys.path adjustment + RealRecordedEvent construction) was
verified separately against a structurally-accurate stand-in package
before these tests were written.
"""

from unittest.mock import patch

from app.services.intelligence_client import IntelligenceProcessingError

# A representative raw Recorder payload, mirroring the actual
# RecordedEvent wire contract exactly (id, type, timestamp, pageUrl,
# targetTag?, elementId?, elementText?, value?, redacted?).
RECORDER_PAYLOAD = {
    "journeyId": "journey-day1-abc",
    "events": [
        {
            "id": "evt-1",
            "type": "page_load",
            "timestamp": 1000.0,
            "pageUrl": "https://example.com",
        },
        {
            "id": "evt-2",
            "type": "click",
            "timestamp": 1500.0,
            "pageUrl": "https://example.com",
            "targetTag": "button",
            "elementId": "submit",
            "elementText": "Submit",
        },
    ],
}

# What Intelligence's pipeline would return for the payload above.
GENERATED_EXECUTION_PAYLOAD = {
    "journeyId": "journey-day1-abc",
    "steps": [
        {"id": "gen-step-evt-1", "type": "navigate", "url": "https://example.com"},
        {"id": "gen-step-evt-2", "type": "click", "selector": "#submit"},
    ],
}


def _create_project(client, name="Recorder Ingestion Project"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


# --- valid Recorder payload -> 201 ---

def test_valid_recorder_payload_is_accepted(client):
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value=GENERATED_EXECUTION_PAYLOAD,
    ) as mock_build:
        response = client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert len(body["content"]) == 2
    mock_build.assert_called_once()


# --- project missing -> 404 ---

def test_recording_requires_existing_project(client):
    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value=GENERATED_EXECUTION_PAYLOAD,
    ) as mock_build:
        response = client.post("/projects/does-not-exist/recordings", json=RECORDER_PAYLOAD)

    assert response.status_code == 404
    # 404 on the project must short-circuit before Intelligence is ever called
    mock_build.assert_not_called()


# --- journeyId becomes the TestDefinition name ---

def test_journey_id_becomes_test_definition_name(client):
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value=GENERATED_EXECUTION_PAYLOAD,
    ):
        response = client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    assert response.json()["name"] == "journey-day1-abc"


# --- real Recorder events are transformed through the existing Intelligence pipeline ---

def test_recorder_events_are_passed_to_intelligence_pipeline(client):
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value=GENERATED_EXECUTION_PAYLOAD,
    ) as mock_build:
        client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    mock_build.assert_called_once()
    called_journey_id, called_events = mock_build.call_args.args
    assert called_journey_id == "journey-day1-abc"
    assert called_events[0]["id"] == "evt-1"
    assert called_events[0]["type"] == "page_load"
    assert called_events[0]["pageUrl"] == "https://example.com"
    assert called_events[1]["elementId"] == "submit"
    # optional fields never supplied must not appear as spurious keys
    assert "value" not in called_events[0]
    assert "redacted" not in called_events[0]


# --- generated step IDs survive ---

def test_generated_step_ids_survive_into_stored_content(client):
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value=GENERATED_EXECUTION_PAYLOAD,
    ):
        response = client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    content = response.json()["content"]
    assert content[0]["id"] == "gen-step-evt-1"
    assert content[1]["id"] == "gen-step-evt-2"


# --- invalid event/step data is rejected appropriately ---

def test_recording_rejects_unknown_event_type(client):
    project_id = _create_project(client)
    payload = {
        "journeyId": "journey-bad",
        "events": [
            {"id": "evt-1", "type": "mouse_hover", "timestamp": 1.0, "pageUrl": "https://example.com"}
        ],
    }

    response = client.post(f"/projects/{project_id}/recordings", json=payload)
    assert response.status_code == 422


def test_recording_rejects_missing_required_event_field(client):
    project_id = _create_project(client)
    # missing required "pageUrl"
    payload = {
        "journeyId": "journey-bad",
        "events": [{"id": "evt-1", "type": "click", "timestamp": 1.0}],
    }

    response = client.post(f"/projects/{project_id}/recordings", json=payload)
    assert response.status_code == 422


def test_recording_rejects_missing_journey_id(client):
    project_id = _create_project(client)
    payload = {"events": RECORDER_PAYLOAD["events"]}

    response = client.post(f"/projects/{project_id}/recordings", json=payload)
    assert response.status_code == 422


def test_recording_returns_422_when_no_steps_could_be_generated(client):
    """
    A well-formed request that Intelligence could genuinely not turn
    into any steps (e.g. every event was unmappable) is a 422, not a
    500/502 — the request was valid, but nothing executable resulted.
    """
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        return_value={"journeyId": "journey-empty", "steps": []},
    ):
        response = client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    assert response.status_code == 422


def test_recording_returns_502_when_intelligence_processing_fails(client):
    project_id = _create_project(client)

    with patch(
        "app.api.routes.recordings.build_execution_payload_from_events",
        side_effect=IntelligenceProcessingError("boom"),
    ):
        response = client.post(f"/projects/{project_id}/recordings", json=RECORDER_PAYLOAD)

    assert response.status_code == 502


# --- empty events are rejected ---

def test_recording_rejects_empty_events_list(client):
    project_id = _create_project(client)
    payload = {"journeyId": "journey-empty-events", "events": []}

    response = client.post(f"/projects/{project_id}/recordings", json=payload)
    assert response.status_code == 422


# --- existing endpoints remain unaffected ---

def test_existing_project_and_test_definition_endpoints_still_work(client):
    """
    Light smoke check that adding the recordings router/CORS middleware
    didn't disturb existing routes. Full coverage of these endpoints
    already lives in test_projects.py / test_test_definitions.py /
    test_execution.py / test_execution_payload_ingestion.py.
    """
    project_response = client.post("/projects", json={"name": "Unaffected Project"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    test_def_response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Still works", "content": [{"type": "navigate", "url": "https://example.com"}]},
    )
    assert test_def_response.status_code == 201

    health_response = client.get("/health")
    assert health_response.status_code == 200
