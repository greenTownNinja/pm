import httpx
import pytest

from app import ai
from app.config import settings


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")


def fake_post(response):
    """Replace AsyncClient.post, recording the call and returning a canned response."""
    calls = []

    async def post(_self, url, **kwargs):
        calls.append({"url": url, **kwargs})
        if isinstance(response, Exception):
            raise response
        return response

    return post, calls


def completion(content):
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        request=httpx.Request("POST", ai.OPENROUTER_URL),
    )


def test_ping_sends_the_expected_request(signed_in, monkeypatch):
    post, calls = fake_post(completion("4"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    response = signed_in.post("/api/ai/ping")

    assert response.status_code == 200
    assert response.json() == {"reply": "4"}
    assert calls[0]["url"] == ai.OPENROUTER_URL
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"]["model"] == "openai/gpt-oss-120b"
    assert calls[0]["json"]["messages"] == [{"role": "user", "content": "What is 2+2?"}]


def test_timeout_surfaces_as_502(signed_in, monkeypatch):
    post, _ = fake_post(httpx.TimeoutException("timed out"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    assert signed_in.post("/api/ai/ping").status_code == 502


def test_upstream_500_surfaces_as_502(signed_in, monkeypatch):
    error = httpx.Response(500, request=httpx.Request("POST", ai.OPENROUTER_URL))
    post, _ = fake_post(error)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    assert signed_in.post("/api/ai/ping").status_code == 502


def test_malformed_response_surfaces_as_502(signed_in, monkeypatch):
    post, _ = fake_post(
        httpx.Response(200, json={}, request=httpx.Request("POST", ai.OPENROUTER_URL))
    )
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    assert signed_in.post("/api/ai/ping").status_code == 502


def test_missing_key_fails_loudly(signed_in, monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    response = signed_in.post("/api/ai/ping")

    assert response.status_code == 500
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_ping_requires_authentication(client):
    assert client.post("/api/ai/ping").status_code == 401
