def test_unauthenticated_participant_access_denied(client):
    # Public / unauthenticated cannot fetch private participant list
    res = client.get("/api/v1/participants")
    assert res.status_code == 401


def test_public_projector_cannot_view_private_participants(client, projector_headers):
    # Public projector cannot access direct participants directory
    res = client.get("/api/v1/participants", headers=projector_headers)
    assert res.status_code == 403


def test_public_teams_endpoint_masks_participant_pii(client, marshal_headers, projector_headers):
    # 1. Create a team and participant with full info as marshal
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Stealth Unit"})
    team_id = t_res.json()["data"]["id"]

    client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Classified Agent",
            "email": "agent@bmsit.in",
            "usn": "1BY22CS999",
            "phone": "+91 99999 88888",
            "role": "Leader",
            "teamId": team_id,
        }
    )

    # 2. Query teams anonymously (Public Projector / Unauthenticated)
    pub_res = client.get("/api/v1/teams")
    assert pub_res.status_code == 200
    teams = pub_res.json()["data"]
    stealth_team = next(t for t in teams if t["id"] == team_id)
    assert len(stealth_team["members"]) == 1
    member = stealth_team["members"][0]
    
    # Public view MUST have PII stripped (None)
    assert member["name"] == "Classified Agent"
    assert member["email"] is None
    assert member["usn"] is None
    assert member["phone"] is None

    # 3. Query teams as Public Projector
    proj_res = client.get("/api/v1/teams", headers=projector_headers)
    assert proj_res.status_code == 200
    member_proj = proj_res.json()["data"][0]["members"][0]
    assert member_proj["email"] is None
    assert member_proj["usn"] is None
    assert member_proj["phone"] is None

    # 4. Query teams as Staff (Marshal / Organizer)
    staff_res = client.get("/api/v1/teams", headers=marshal_headers)
    assert staff_res.status_code == 200
    member_staff = staff_res.json()["data"][0]["members"][0]
    assert member_staff["email"] == "agent@bmsit.in"
    assert member_staff["usn"] == "1BY22CS999"
    assert member_staff["phone"] == "+91 99999 88888"


def test_team_deletion_safely_unassigns_participants(client, organizer_headers, marshal_headers):
    # Create team & participant
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Temporary Squad"})
    team_id = t_res.json()["data"]["id"]

    p_res = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Surviving Participant",
            "email": "survivor@bmsit.in",
            "usn": "1BY22CS777",
            "role": "Leader",
            "teamId": team_id,
        }
    )
    p_id = p_res.json()["data"]["id"]

    # Delete team as organizer
    del_res = client.delete(f"/api/v1/teams/{team_id}", headers=organizer_headers)
    assert del_res.status_code == 200

    # Verify participant was NOT deleted, but unassigned to pool
    survivor_res = client.get(f"/api/v1/participants/{p_id}", headers=organizer_headers)
    assert survivor_res.status_code == 200
    survivor = survivor_res.json()["data"]
    assert survivor["teamId"] is None
    assert survivor["role"] == "Member"


def test_sequential_transfer_capacity_rejection(client, marshal_headers):
    # Setup team
    t_res = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Max Squad"})
    team_id = t_res.json()["data"]["id"]

    # Fill team with 5 members
    for i in range(1, 6):
        res = client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Squad Member {i}",
                "email": f"squad{i}@bmsit.in",
                "usn": f"1BY22CS88{i}",
                "teamId": team_id,
            }
        )
        assert res.status_code == 201

    # Attempt to transfer another participant into full squad
    p_free = client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Overflow Member",
            "email": "overflow@bmsit.in",
            "usn": "1BY22CS899",
        }
    ).json()["data"]["id"]

    transfer_res = client.post(
        f"/api/v1/participants/{p_free}/transfer",
        headers=marshal_headers,
        json={"targetTeamId": team_id}
    )
    assert transfer_res.status_code == 400
    assert "maximum squad limit of 5" in transfer_res.json()["message"]


def test_rbac_unauthorized_and_forbidden_matrix(client, judge_headers, marshal_headers, organizer_headers):
    # 1. Unauthenticated mutations -> 401
    assert client.post("/api/v1/teams", json={"name": "No Auth"}).status_code == 401
    assert client.post("/api/v1/participants", json={"name": "No Auth", "email": "a@b.com", "usn": "1BY22CS991"}).status_code == 401
    assert client.patch("/api/v1/settings", json={"eventName": "No Auth"}).status_code == 401
    assert client.post("/api/v1/auth/register", json={"email": "a@b.com", "name": "A", "password": "Pass", "role": "MARSHAL"}).status_code == 401

    # 2. Judge mutations -> 403 Forbidden
    assert client.post("/api/v1/teams", headers=judge_headers, json={"name": "Judge Team"}).status_code == 403
    assert client.post("/api/v1/participants", headers=judge_headers, json={"name": "Judge Part", "email": "j@b.com", "usn": "1BY22CS992"}).status_code == 403
    assert client.patch("/api/v1/settings", headers=judge_headers, json={"eventName": "Judge Event"}).status_code == 403

    # 3. Marshal privileged actions -> 403 Forbidden (Only Organizer can delete team or edit settings)
    t_id = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Marshal Team"}).json()["data"]["id"]
    p_id = client.post("/api/v1/participants", headers=marshal_headers, json={"name": "Marshal Part", "email": "m@b.com", "usn": "1BY22CS993"}).json()["data"]["id"]
    
    assert client.delete(f"/api/v1/teams/{t_id}", headers=marshal_headers).status_code == 403
    assert client.delete(f"/api/v1/participants/{p_id}", headers=marshal_headers).status_code == 403
    assert client.patch("/api/v1/settings", headers=marshal_headers, json={"eventName": "Marshal Event"}).status_code == 403

    # 4. Organizer executing privileged actions -> 200 OK
    assert client.delete(f"/api/v1/teams/{t_id}", headers=organizer_headers).status_code == 200
    assert client.delete(f"/api/v1/participants/{p_id}", headers=organizer_headers).status_code == 200