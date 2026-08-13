import httpx
from fastapi import APIRouter, HTTPException

from app.auth import CurrentUser
from app.config import settings

router = APIRouter(prefix="/api/ai")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"
TIMEOUT = 60.0


async def complete(messages: list[dict[str, str]]) -> str:
    """Send a chat completion to OpenRouter and return the reply text."""
    if not settings.openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set")

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json={"model": MODEL, "messages": messages},
            )
    except httpx.HTTPError as exc:
        # Timeouts and connection failures are the upstream's problem, not a 500 here.
        raise HTTPException(
            status_code=502, detail=f"AI request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI request failed with status {response.status_code}",
        )

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=502, detail="AI response was malformed"
        ) from exc


@router.post("/ping")
async def ping(_user: CurrentUser) -> dict[str, str]:
    """Temporary proof that the OpenRouter call works. Removed in Part 10."""
    reply = await complete([{"role": "user", "content": "What is 2+2?"}])
    return {"reply": reply}
