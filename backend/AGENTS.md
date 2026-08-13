# Backend

Python FastAPI service. It serves the JSON API under `/api` and the built frontend at `/`.
Dependencies are managed with `uv`; the app runs in a Docker container.

## Layout

```
pyproject.toml    uv-managed dependencies, pytest and ruff config
app/config.py     Settings, read from the environment or the project root .env
app/main.py       FastAPI app: API routes, then the static mount
static/           what gets served at / (placeholder now, the Next export from Part 3)
tests/            pytest suite
```

## Conventions

- API routes live under `/api`. The static mount at `/` is registered **last** so it only
  catches paths the API did not claim.
- `SPAStaticFiles` falls back to `index.html` on a 404 so client-side routes resolve.
- Configuration goes through `app.config.settings`, never `os.environ` directly. The
  project root `.env` supplies `OPENROUTER_API_KEY` and `SESSION_SECRET`; in the container
  they arrive as environment variables via `--env-file`.
- `STATIC_DIR` and other paths come from `app/config.py`, resolved from `__file__`, so they
  work the same locally and in the container.

## Running

From the project root, `scripts/start.sh` (or `start.ps1`) builds the image and runs it as
the container `pm-app` on port 8000, with the named volume `pm-data` mounted at
`/app/data` for the SQLite file. `scripts/stop.sh` removes the container. No compose file -
plain `docker build` and `docker run`.

For a local loop without Docker: `uv sync` then
`uv run uvicorn app.main:app --reload` from `backend/`.

## Tests and linting

`uv run pytest` from `backend/`. Tests use `fastapi.testclient.TestClient` and import the
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

Database, auth, board routes and AI live in Parts 4 through 9 of `docs/PLAN.md`.
