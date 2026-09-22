def test_duplicate_team_names_case_and_whitespace(client, marshal_headers):
    # 1. Create initial team
    res1 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Vanguard Elite"})
    assert res1.status_code == 201

    # 2. Duplicate with uppercase & trailing whitespace -> 400
    res2 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "  VANGUARD ELITE  "})
    assert res2.status_code == 400
    assert "already exists" in res2.json()["message"]


def test_duplicate_usn_case_and_whitespace(client, marshal_headers):
    # 1. Create participant with lowercase & whitespace
    res1 = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Cadet One", "email": "cadet1@bmsit.in", "usn": "  1by22cs501  "}
    )
    assert res1.status_code == 201
    assert res1.json()["data"]["usn"] == "1BY22CS501"

    # 2. Attempt duplicate with uppercase
    res2 = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Cadet Duplicate", "email": "dup@bmsit.in", "usn": "1BY22CS501"}
    )
    assert res2.status_code == 400
    assert "already registered" in res2.json()["message"]


def test_nonexistent_team_id_rejected(client, marshal_headers):
    # Create participant with invalid teamId -> 404
    res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Lost Cadet", "email": "lost@bmsit.in", "usn": "1BY22CS502", "teamId": "nonexistent-team-999"}
    )
    assert res.status_code == 404
    assert "does not exist" in res.json()["message"]


def test_invalid_request_body_validation(client, marshal_headers):
    # Missing required name & invalid email -> 422
    res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"email": "not-an-email", "usn": "1BY22CS503"}
    )
    assert res.status_code == 422
    assert "Validation Error" in res.json()["message"]


def test_empty_and_whitespace_search_parameters(client, marshal_headers):
    client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Searchable Cadet", "email": "search@bmsit.in", "usn": "1BY22CS504"}
    )

    # Empty search string returns all results
    res_empty = client.get("/api/v1/participants?search=", headers=marshal_headers)
    assert res_empty.status_code == 200
    assert len(res_empty.json()["data"]) >= 1

    # Whitespace search string returns all results
    res_ws = client.get("/api/v1/participants?search=   ", headers=marshal_headers)
    assert res_ws.status_code == 200
    assert len(res_ws.json()["data"]) >= 1