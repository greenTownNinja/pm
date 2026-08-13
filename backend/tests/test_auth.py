from fastapi.testclient import TestClient

from app.main import app

GOOD = {"username": "user", "password": "password"}


def test_login_with_correct_credentials_sets_a_session_cookie():
    with TestClient(app) as client:
        response = client.post("/api/login", json=GOOD)
        assert response.status_code == 200
        assert response.json() == {"username": "user"}
        assert "session" in client.cookies


def test_login_with_wrong_password_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/login", json={"username": "user", "password": "nope"}
        )
        assert response.status_code == 401
        assert "session" not in client.cookies


def test_guarded_route_requires_a_session():
    with TestClient(app) as client:
        assert client.get("/api/me").status_code == 401
        client.post("/api/login", json=GOOD)
        response = client.get("/api/me")
        assert response.status_code == 200
        assert response.json() == {"username": "user"}


def test_logout_invalidates_the_session():
    with TestClient(app) as client:
        client.post("/api/login", json=GOOD)
        assert client.post("/api/logout").status_code == 200
        assert client.get("/api/me").status_code == 401


def test_session_cookie_is_httponly():
    with TestClient(app) as client:
        response = client.post("/api/login", json=GOOD)
        set_cookie = response.headers["set-cookie"]
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()


def test_health_is_not_guarded():
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
