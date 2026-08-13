import pytest
from fastapi.testclient import TestClient

from app.config import STATIC_DIR
from app.main import app

client = TestClient(app)

# The Next export is a build artifact, not checked in. Produce it with
# `npm run build:static` from frontend/; the container image always has it.
pytestmark = pytest.mark.skipif(
    not (STATIC_DIR / "index.html").exists(),
    reason="frontend not built into backend/static",
)


def test_root_serves_the_next_export():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Kanban Studio" in response.text


def test_known_asset_is_served():
    asset = next((STATIC_DIR / "_next").rglob("*.js"))
    response = client.get(f"/{asset.relative_to(STATIC_DIR)}")
    assert response.status_code == 200


def test_unknown_api_path_is_a_404():
    response = client.get("/api/nope")
    assert response.status_code == 404


def test_unknown_path_falls_back_to_index():
    response = client.get("/some/client/route")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Kanban Studio" in response.text
