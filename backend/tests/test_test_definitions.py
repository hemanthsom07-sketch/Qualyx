STEP_CONTENT = [
    {"type": "navigate", "url": "https://example.com"},
    {"type": "click", "selector": "#submit"},
    {"type": "fill", "selector": "#email", "value": "user@example.com"},
]


def _create_project(client, name="Project For Tests"):
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def test_create_test_definition(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Login flow", "description": "Basic login", "content": STEP_CONTENT},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Login flow"
    assert body["project_id"] == project_id
    assert body["content"] == STEP_CONTENT
    assert "id" in body
    assert "created_at" in body


def test_create_test_definition_requires_existing_project(client):
    response = client.post(
        "/projects/does-not-exist/tests",
        json={"name": "Orphan test", "content": STEP_CONTENT},
    )
    assert response.status_code == 404


def test_create_test_definition_rejects_empty_content(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Empty test", "content": []},
    )
    assert response.status_code == 422


def test_create_test_definition_rejects_unknown_step_type(client):
    project_id = _create_project(client)

    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Bad step", "content": [{"type": "hover", "selector": "#x"}]},
    )
    assert response.status_code == 422


def test_create_test_definition_rejects_missing_step_fields(client):
    project_id = _create_project(client)

    # "fill" step missing required "selector"
    response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Bad fill", "content": [{"type": "fill", "value": "hi"}]},
    )
    assert response.status_code == 422


def test_get_test_definition(client):
    project_id = _create_project(client)
    create_response = client.post(
        f"/projects/{project_id}/tests",
        json={"name": "Retrievable test", "content": STEP_CONTENT},
    )
    test_id = create_response.json()["id"]

    get_response = client.get(f"/tests/{test_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == test_id


def test_get_test_definition_not_found(client):
    response = client.get("/tests/does-not-exist")
    assert response.status_code == 404


def test_list_test_definitions_for_project(client):
    project_id = _create_project(client)
    client.post(f"/projects/{project_id}/tests", json={"name": "Test A", "content": STEP_CONTENT})
    client.post(f"/projects/{project_id}/tests", json={"name": "Test B", "content": STEP_CONTENT})

    other_project_id = _create_project(client, name="Other Project")
    client.post(f"/projects/{other_project_id}/tests", json={"name": "Should not appear", "content": STEP_CONTENT})

    response = client.get(f"/projects/{project_id}/tests")
    assert response.status_code == 200
    names = [t["name"] for t in response.json()]
    assert names == ["Test B", "Test A"]  # newest first
    assert "Should not appear" not in names


def test_list_test_definitions_requires_existing_project(client):
    response = client.get("/projects/does-not-exist/tests")
    assert response.status_code == 404
