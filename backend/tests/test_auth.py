from tests.conftest import CREDENTIALS


def test_login_with_correct_credentials_sets_a_session_cookie(client):
    response = client.post("/api/login", json=CREDENTIALS)
    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    assert "session" in client.cookies


def test_login_with_wrong_password_is_rejected(client):
    response = client.post("/api/login", json={"username": "user", "password": "nope"})
    assert response.status_code == 401
    assert "session" not in client.cookies


def test_login_with_unknown_user_is_rejected(client):
    response = client.post("/api/login", json={"username": "ghost", "password": "x"})
    assert response.status_code == 401


def test_guarded_route_requires_a_session(client):
    assert client.get("/api/me").status_code == 401
    client.post("/api/login", json=CREDENTIALS)
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json() == {"username": "user"}


def test_logout_invalidates_the_session(signed_in):
    assert signed_in.post("/api/logout").status_code == 200
    assert signed_in.get("/api/me").status_code == 401


def test_session_cookie_is_httponly(client):
    response = client.post("/api/login", json=CREDENTIALS)
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie


def test_health_is_not_guarded(client):
    assert client.get("/api/health").status_code == 200
