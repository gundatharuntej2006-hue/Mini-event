def test_get_and_update_settings(client, organizer_headers, marshal_headers):
    # Get initial settings
    res_get = client.get("/api/v1/settings")
    assert res_get.status_code == 200
    data = res_get.json()["data"]
    assert "eventName" in data
    assert data["tableCount"] == 32

    # Update as Organizer
    res_update = client.patch(
        "/api/v1/settings",
        headers=organizer_headers,
        json={"eventName": "EVENT HQ 2026 FINALS", "tableCount": 48}
    )
    assert res_update.status_code == 200
    assert res_update.json()["data"]["eventName"] == "EVENT HQ 2026 FINALS"
    assert res_update.json()["data"]["tableCount"] == 48

    # Attempt update as Marshal (Forbidden)
    res_forbidden = client.patch(
        "/api/v1/settings",
        headers=marshal_headers,
        json={"eventName": "Unauthorized Edit"}
    )
    assert res_forbidden.status_code == 403