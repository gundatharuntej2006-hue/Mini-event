def test_create_participant_and_usn_normalization(client, marshal_headers):
    # Create a team
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Delta Force"})
    team_id = t_res.json()["data"]["id"]

    # Create participant with lowercase usn
    p_res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Alice Johnson",
            "email": "alice@bmsit.in",
            "usn": "1by22cs001",
            "role": "Leader",
            "teamId": team_id,
            "checkedIn": True,
        }
    )
    assert p_res.status_code == 201
    p_data = p_res.json()["data"]
    assert p_data["name"] == "Alice Johnson"
    assert p_data["usn"] == "1BY22CS001"  # Normalized to uppercase
    assert p_data["checkedIn"] is True
    assert p_data["checkedInAt"] is not None
    assert p_data["teamId"] == team_id


def test_duplicate_usn_rejected(client, marshal_headers):
    client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Bob", "email": "bob@bmsit.in", "usn": "1BY22CS002"}
    )
    res_dup = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Bob Duplicate", "email": "bob2@bmsit.in", "usn": "1by22cs002"}
    )
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["message"]


def test_5_person_squad_capacity_limit(client, marshal_headers):
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Squad Five"})
    team_id = t_res.json()["data"]["id"]

    # Add 5 participants (all succeed)
    for i in range(1, 6):
        res = client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Member {i}",
                "email": f"member{i}@bmsit.in",
                "usn": f"1BY22CS01{i}",
                "teamId": team_id,
            }
        )
        assert res.status_code == 201

    # Attempt to add 6th member -> must fail with 400 Bad Request
    res_6th = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Member 6",
            "email": "member6@bmsit.in",
            "usn": "1BY22CS016",
            "teamId": team_id,
        }
    )
    assert res_6th.status_code == 400
    assert "maximum squad limit of 5" in res_6th.json()["message"]


def test_participant_checkin_toggle(client, marshal_headers):
    p_res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Charlie", "email": "charlie@bmsit.in", "usn": "1BY22CS020", "checkedIn": False}
    )
    p_id = p_res.json()["data"]["id"]
    assert p_res.json()["data"]["checkedIn"] is False
    assert p_res.json()["data"]["checkedInAt"] is None

    # Check In
    check_res = client.patch(
        f"/api/v1/participants/{p_id}/check-in",
        headers=marshal_headers,
        json={"checkedIn": True}
    )
    assert check_res.status_code == 200
    assert check_res.json()["data"]["checkedIn"] is True
    assert check_res.json()["data"]["checkedInAt"] is not None

    # Undo Check In
    uncheck_res = client.patch(
        f"/api/v1/participants/{p_id}/check-in",
        headers=marshal_headers,
        json={"checkedIn": False}
    )
    assert uncheck_res.status_code == 200
    assert uncheck_res.json()["data"]["checkedIn"] is False
    assert uncheck_res.json()["data"]["checkedInAt"] is None


def test_participant_transfer_and_unassignment(client, marshal_headers):
    t1 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Team Alpha"}).json()["data"]["id"]
    t2 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Team Beta"}).json()["data"]["id"]

    p_res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={"name": "Dave", "email": "dave@bmsit.in", "usn": "1BY22CS030", "teamId": t1}
    )
    p_id = p_res.json()["data"]["id"]

    # 1. Transfer to Team Beta
    trans_res = client.post(
        f"/api/v1/participants/{p_id}/transfer",
        headers=marshal_headers,
        json={"targetTeamId": t2}
    )
    assert trans_res.status_code == 200
    assert trans_res.json()["data"]["teamId"] == t2
    assert trans_res.json()["data"]["teamName"] == "Team Beta"

    # 2. Unassign participant to pool (targetTeamId = null)
    unassign_res = client.post(
        f"/api/v1/participants/{p_id}/transfer",
        headers=marshal_headers,
        json={"targetTeamId": None}
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["data"]["teamId"] is None


def test_update_participant_team_capacity_validation(client, marshal_headers):
    t_full = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Full Squad"}).json()["data"]["id"]
    t_origin = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Origin Squad"}).json()["data"]["id"]

    # Fill t_full with 5 members
    for i in range(1, 6):
        client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Full Member {i}",
                "email": f"full{i}@bmsit.in",
                "usn": f"1BY22CS30{i}",
                "teamId": t_full,
            }
        )

    # Create participant in t_origin
    p_res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Mover",
            "email": "mover@bmsit.in",
            "usn": "1BY22CS399",
            "teamId": t_origin,
        }
    )
    p_id = p_res.json()["data"]["id"]

    # Attempt PUT update with teamId = t_full -> must fail with 400
    put_res = client.put(
        f"/api/v1/participants/{p_id}",
        headers=marshal_headers,
        json={"teamId": t_full}
    )
    assert put_res.status_code == 400
    assert "maximum squad limit of 5" in put_res.json()["message"]

    # Verify participant is still in t_origin
    check_res = client.get(f"/api/v1/participants/{p_id}", headers=marshal_headers)
    assert check_res.json()["data"]["teamId"] == t_origin