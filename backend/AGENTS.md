# Backend

Python FastAPI service. It serves the JSON API under `/api` and the built frontend at `/`.
Dependencies are managed with `uv`; the app runs in a Docker container.

## Layout

```
pyproject.toml    uv-managed dependencies, pytest and ruff config
app/config.py     Settings, read from the environment or the project root .env
app/main.py       FastAPI app: session middleware, API routes, then the static mount
app/auth.py       login / logout / me, and the require_user dependency
static/           the Next static export, served at / (build artifact, gitignored)
tests/            pytest suite
```

## Conventions

- API routes live under `/api`. The static mount at `/` is registered **last** so it only
  catches paths the API did not claim.
- `SPAStaticFiles` falls back to `index.html` so client-side routes resolve. It handles
  both 404 shapes: `StaticFiles` raises for a missing path, but with `html=True` it serves
  the export's own `404.html` as a 404 *response* instead, so the status is checked too.
  Paths under `api/` never fall back - an unmatched API path is a 404, not the board HTML.
- Configuration goes through `app.config.settings`, never `os.environ` directly. The
  project root `.env` supplies `OPENROUTER_API_KEY` and `SESSION_SECRET`; in the container
  they arrive as environment variables via `--env-file`.
- `STATIC_DIR` and other paths come from `app/config.py`, resolved from `__file__`, so they
  work the same locally and in the container.

## Auth

Starlette `SessionMiddleware` signs an HttpOnly, SameSite=Lax cookie with
`settings.session_secret`. `POST /api/login` validates against the hardcoded `user` /
`password` in `app/auth.py` (Part 6 replaces this with a users table) and writes
`username` into the session; `POST /api/logout` clears it.

Every `/api` route except `login`, `logout` and `health` takes the current user through the
`CurrentUser` annotation (`Annotated[User, Depends(require_user)]`), which 401s when there
is no session. New routes added in later parts follow that pattern.

## Static files

`static/` holds the Next export and is a build artifact - gitignored apart from
`.gitkeep`, which keeps the directory present so the mount resolves on a fresh clone.
Populate it with `npm run build:static` from `frontend/`. The Docker build instead copies
`out/` from the node stage, and `.dockerignore` excludes `backend/static` so the host copy
never leaks into the image.

Tests that need the export skip themselves when it is absent (`tests/test_static.py`).

## Running

From the project root, `scripts/start.sh` (or `start.ps1`) builds the image and runs it as
the container `pm-app` on port 8000, with the named volume `pm-data` mounted at
`/app/data` for the SQLite file. `scripts/stop.sh` removes the container. No compose file -
plain `docker build` and `docker run`.

For a local loop without Docker: `uv sync` then
`uv run uvicorn app.main:app --reload` from `backend/`.

## Tests and linting

`uv run pytest` from `backend/`. The static tests are skipped unless the frontend has been
built into `static/`. Tests use `fastapi.testclient.TestClient` and import the
app as `from app.main import app`; `pythonpath = ["."]` in `pyproject.toml` puts `backend/`
on `sys.path`, so pytest must run with `backend/` as the working directory.

To run them in the container: `docker exec pm-app pytest`.

Ruff is the linter and formatter. Run both before committing Python changes:

```
uv run ruff check .      # add --fix to apply safe fixes
uv run ruff format .
```

Rules selected: `E`, `F`, `I`, `UP`, `B` (pycodestyle, pyflakes, isort, pyupgrade,
bugbear). Keep imports sorted by ruff rather than by hand.

## Not built yet

Database, board routes and AI live in Parts 5 through 9 of `docs/PLAN.md`.
