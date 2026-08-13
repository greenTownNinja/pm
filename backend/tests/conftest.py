import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.main import app

CREDENTIALS = {"username": "user", "password": "password"}


@pytest.fixture
def client(tmp_path):
    """A client on a temporary database, seeded by the app's own startup."""
    db.configure(tmp_path / "pm.db")
    with TestClient(app) as test_client:
        yield test_client
    db.configure(settings.database_path)


@pytest.fixture
def signed_in(client):
    client.post("/api/login", json=CREDENTIALS)
    return client
