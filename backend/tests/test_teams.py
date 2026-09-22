def test_create_and_list_teams(client, marshal_headers):
    # Create Team
    res_create = client.post(
        "/api/v1/teams",
        headers=marshal_headers,
        json={"name": "Cyber Hawks", "assignedTable": "Table 1"}
    )
    assert res_create.status_code == 201
    created_team = res_create.json()["data"]
    assert created_team["name"] == "Cyber Hawks"
    assert created_team["teamNumber"] == 1
    assert created_team["assignedTable"] == "Table 1"

    # List Teams
    res_list = client.get("/api/v1/teams")
    assert res_list.status_code == 200
    teams = res_list.json()["data"]
    assert len(teams) == 1
    assert teams[0]["name"] == "Cyber Hawks"


def test_duplicate_team_name_rejected(client, marshal_headers):
    client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Alpha Squad"})
    res_duplicate = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "alpha squad"})
    assert res_duplicate.status_code == 400
    assert "already exists" in res_duplicate.json()["message"]


def test_update_team(client, marshal_headers):
    res_create = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Beta Unit"})
    team_id = res_create.json()["data"]["id"]

    res_update = client.put(
        f"/api/v1/teams/{team_id}",
        headers=marshal_headers,
        json={"name": "Beta Unit Prime", "assignedTable": "Table 42"}
    )
    assert res_update.status_code == 200
    assert res_update.json()["data"]["name"] == "Beta Unit Prime"
    assert res_update.json()["data"]["assignedTable"] == "Table 42"


def test_delete_team(client, organizer_headers, marshal_headers):
    res_create = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Gamma Team"})
    team_id = res_create.json()["data"]["id"]

    # Delete as organizer
    res_delete = client.delete(f"/api/v1/teams/{team_id}", headers=organizer_headers)
    assert res_delete.status_code == 200

    # Verify not found
    res_get = client.get(f"/api/v1/teams/{team_id}")
    assert res_get.status_code == 404