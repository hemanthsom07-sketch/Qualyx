def test_create_project(client):
    response = client.post("/projects", json={"name": "Demo Project", "description": "A test project"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Demo Project"
    assert body["description"] == "A test project"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_project_requires_name(client):
    response = client.post("/projects", json={"description": "missing name"})
    assert response.status_code == 422


def test_get_project(client):
    create_response = client.post("/projects", json={"name": "Retrievable Project"})
    project_id = create_response.json()["id"]

    get_response = client.get(f"/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == project_id
    assert get_response.json()["name"] == "Retrievable Project"


def test_get_project_not_found(client):
    response = client.get("/projects/does-not-exist")
    assert response.status_code == 404


def test_list_projects(client):
    client.post("/projects", json={"name": "Project A"})
    client.post("/projects", json={"name": "Project B"})

    response = client.get("/projects")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Project A" in names
    assert "Project B" in names
