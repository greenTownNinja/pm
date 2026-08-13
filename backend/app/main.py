from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.types import Scope

from app.config import STATIC_DIR

app = FastAPI(title="Project Management MVP")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class SPAStaticFiles(StaticFiles):
    """Serve the built frontend, falling back to index.html for client-side routes."""

    async def get_response(self, path: str, scope: Scope):
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
        # With html=True a missing path is served as the export's own 404.html rather
        # than raised, so the status has to be checked too.
        if response.status_code == 404:
            return await super().get_response("index.html", scope)
        return response


# Mounted last so it only catches paths the API routes above did not claim.
app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="static")
