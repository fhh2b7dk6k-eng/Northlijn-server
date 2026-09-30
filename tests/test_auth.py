def signup(client, email="athlete@example.com", password="correct-horse"):
    return client.post("/auth/signup", json={"email": email, "password": password})


def test_signup_returns_token_pair(client):
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_signup_normalizes_email_case(client):
    signup(client, email="Athlete@Example.com")
    response = client.post("/auth/login", json={"email": "athlete@example.com", "password": "correct-horse"})
    assert response.status_code == 200


def test_signup_duplicate_email_returns_409(client):
    signup(client)
    response = signup(client)
    assert response.status_code == 409


def test_signup_rejects_short_password(client):
    response = signup(client, password="short")
    assert response.status_code == 422


def test_login_success(client):
    signup(client)
    response = client.post("/auth/login", json={"email": "athlete@example.com", "password": "correct-horse"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_returns_generic_401(client):
    signup(client)
    response = client.post("/auth/login", json={"email": "athlete@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_returns_same_generic_401(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_requires_authentication(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_me_returns_current_user(client):
    tokens = signup(client).json()
    response = client.get("/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == "athlete@example.com"


def test_me_rejects_garbage_token(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_refresh_issues_new_pair_and_revokes_old(client):
    tokens = signup(client).json()

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # The original refresh token was rotated out — reusing it must fail.
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    # The new refresh token works.
    again = client.post("/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert again.status_code == 200


def test_refresh_rejects_unknown_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-real-refresh-token"})
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = signup(client).json()

    logout_response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_logout_is_idempotent(client):
    tokens = signup(client).json()
    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    second_call = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert second_call.status_code == 204


def test_delete_account_requires_authentication(client):
    response = client.delete("/users/me")
    assert response.status_code == 401


def test_delete_account_removes_user_and_revokes_access(client):
    tokens = signup(client).json()
    auth_header = {"Authorization": f"Bearer {tokens['access_token']}"}

    delete_response = client.delete("/users/me", headers=auth_header)
    assert delete_response.status_code == 204

    # Signing up again with the same email must now succeed — the account
    # is genuinely gone, not just hidden.
    second_signup = signup(client)
    assert second_signup.status_code == 201

    # The old refresh token must no longer work either.
    refresh_attempt = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_attempt.status_code == 401


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
