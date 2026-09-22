def test_dashboard_overview_metrics(client, marshal_headers):
    # Setup 1 full team of 5 checked-in participants and 1 partial team
    t1 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Alpha Full"}).json()["data"]["id"]
    for i in range(1, 6):
        client.post(
            "/api/v1/participants",
            headers=marshal_headers,
            json={
                "name": f"Alpha Member {i}",
                "email": f"alpha{i}@bmsit.in",
                "usn": f"1BY22CS10{i}",
                "teamId": t1,
                "checkedIn": True,
            }
        )

    t2 = client.post("/api/v1/teams", headers=marshal_headers, json={"name": "Beta Incomplete"}).json()["data"]["id"]
    client.post(
        "/api/v1/participants",
        headers=marshal_headers,
        json={
            "name": "Beta Member 1",
            "email": "beta1@bmsit.in",
            "usn": "1BY22CS201",
            "teamId": t2,
            "checkedIn": False,
        }
    )

    res = client.get("/api/v1/dashboard/overview")
    assert res.status_code == 200
    data = res.json()["data"]
    stats = data["stats"]
    
    assert stats["totalTeams"] == 2
    assert stats["totalParticipants"] == 6
    assert stats["checkedInParticipants"] == 5
    assert stats["completeRosterTeams"] == 1
    assert stats["incompleteRosterTeams"] == 1
    assert stats["checkedInTeams"] == 1
    assert stats["activeTeamsRemaining"] == 2

    # Verify tournament progression pipeline contract
    assert "progression" in data
    progression = data["progression"]
    assert isinstance(progression, list)
    assert len(progression) == 5

    r1 = progression[0]
    assert r1["roundNumber"] == 1
    assert r1["totalPool"] == 32
    assert r1["qualifyingCount"] == 24
    assert r1["status"] in ["Live", "In Progress", "Completed", "Scheduled"]

    r2 = progression[1]
    assert r2["roundNumber"] == 2
    assert r2["totalPool"] == 24
    assert r2["qualifyingCount"] == 12

    r5 = progression[4]
    assert r5["roundNumber"] == 5
    assert r5["totalPool"] == 3
    assert r5["qualifyingCount"] == 1

    # Verify recentActivities contract
    assert "recentActivities" in data
    assert isinstance(data["recentActivities"], list)


def test_dashboard_empty_state_and_safe_contract(client):
    """Test dashboard endpoint when no teams or participants exist."""
    res = client.get("/api/v1/dashboard/overview")
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert "stats" in data
    assert "progression" in data
    assert "recentActivities" in data
    
    assert isinstance(data["progression"], list)
    assert len(data["progression"]) == 5
    for step in data["progression"]:
        assert "roundNumber" in step
        assert "name" in step
        assert "qualifyingCount" in step
        assert "totalPool" in step
        assert "status" in step
    
    assert isinstance(data["recentActivities"], list)