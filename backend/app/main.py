from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import Scope

from app import ai, auth, board
from app.config import STATIC_DIR, settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    init_db()
    yield


app = FastAPI(title="Project Management MVP", lifespan=lifespan)

# Signed HttpOnly cookie; SessionMiddleware always sets HttpOnly.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(board.router)
app.include_router(ai.router)


class SPAStaticFiles(StaticFiles):
    """Serve the built frontend, falling back to index.html for client-side routes."""

    async def get_response(self, path: str, scope: Scope):
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return await self.fallback(path, scope)
        # With html=True a missing path is served as the export's own 404.html rather
        # than raised, so the status has to be checked too.
        if response.status_code == 404:
            return await self.fallback(path, scope)
        return response

    async def fallback(self, path: str, scope: Scope):
        # An unmatched /api path is a missing API route, not a client-side route.
        # Without this it would resolve to index.html with a 200.
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        return await super().get_response("index.html", scope)


# Mounted last so it only catches paths the API routes above did not claim.
app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="static")
