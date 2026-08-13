import httpx
import pytest
from fastapi import HTTPException

from app import ai
from app.config import settings

MESSAGES = [{"role": "user", "content": "What is 2+2?"}]


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")


def stub_post(monkeypatch, response):
    """Replace AsyncClient.post, recording the call and returning a canned response."""
    calls = []

    async def post(_self, url, **kwargs):
        calls.append({"url": url, **kwargs})
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    return calls


def completion(content):
    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        request=httpx.Request("POST", ai.OPENROUTER_URL),
    )


@pytest.mark.asyncio
async def test_sends_the_expected_request(monkeypatch):
    calls = stub_post(monkeypatch, completion("4"))

    assert await ai.complete(MESSAGES) == "4"
    assert calls[0]["url"] == ai.OPENROUTER_URL
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"] == {"model": "openai/gpt-4o-mini", "messages": MESSAGES}


@pytest.mark.asyncio
async def test_a_response_format_pins_the_provider(monkeypatch):
    calls = stub_post(monkeypatch, completion("{}"))
    response_format = {"type": "json_schema"}

    await ai.complete(MESSAGES, response_format=response_format)

    assert calls[0]["json"]["response_format"] == response_format
    # Without this OpenRouter may route to a provider that ignores the schema.
    assert calls[0]["json"]["provider"] == {"require_parameters": True}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        pytest.param(httpx.TimeoutException("timed out"), id="timeout"),
        pytest.param(httpx.ConnectError("refused"), id="connection"),
        pytest.param(
            httpx.Response(500, request=httpx.Request("POST", ai.OPENROUTER_URL)),
            id="upstream 500",
        ),
        pytest.param(
            httpx.Response(
                200, json={}, request=httpx.Request("POST", ai.OPENROUTER_URL)
            ),
            id="malformed body",
        ),
    ],
)
async def test_upstream_failures_are_502(monkeypatch, response):
    stub_post(monkeypatch, response)

    with pytest.raises(HTTPException) as raised:
        await ai.complete(MESSAGES)

    assert raised.value.status_code == 502


@pytest.mark.asyncio
async def test_missing_key_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    with pytest.raises(HTTPException) as raised:
        await ai.complete(MESSAGES)

    assert raised.value.status_code == 500
    assert "OPENROUTER_API_KEY" in raised.value.detail
