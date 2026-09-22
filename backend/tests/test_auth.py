def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test_organizer@bmsit.in", "password": "OrganizerSecret123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "accessToken" in data["data"]
    assert data["data"]["user"]["email"] == "test_organizer@bmsit.in"
    assert data["data"]["user"]["role"] == "ORGANIZER"


def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "test_organizer@bmsit.in", "password": "WrongPassword"}
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["message"]


def test_get_current_user_me(client, organizer_headers):
    response = client.get("/api/v1/auth/me", headers=organizer_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "test_organizer@bmsit.in"


def test_register_user_as_organizer(client, organizer_headers):
    response = client.post(
        "/api/v1/auth/register",
        headers=organizer_headers,
        json={
            "email": "new_marshal@bmsit.in",
            "name": "New Marshal",
            "password": "SecurePassword123",
            "role": "MARSHAL",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == "new_marshal@bmsit.in"
    assert data["data"]["role"] == "MARSHAL"


def test_register_user_as_marshal_forbidden(client, marshal_headers):
    response = client.post(
        "/api/v1/auth/register",
        headers=marshal_headers,
        json={
            "email": "another@bmsit.in",
            "name": "Another User",
            "password": "SecurePassword123",
            "role": "MARSHAL",
        }
    )
    assert response.status_code == 403