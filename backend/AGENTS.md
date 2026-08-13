# Backend

Python FastAPI service. It serves the JSON API under `/api` and the built frontend at `/`.
Dependencies are managed with `uv`; the app runs in a Docker container.

## Layout

```
pyproject.toml    uv-managed dependencies, pytest and ruff config
app/config.py     Settings, read from the environment or the project root .env
app/main.py       FastAPI app: session middleware, API routes, then the static mount
app/auth.py       login / logout / me, and the require_user dependency
app/board.py      board read and mutation routes
app/db.py         engine, session factory, init_db
app/models.py     SQLAlchemy models for the five tables
app/schemas.py    Pydantic request and response models
app/seed.py       the demo user, board, columns and cards
app/security.py   pbkdf2 password hashing
static/           the Next static export, served at / (build artifact, gitignored)
data/             local SQLite file (gitignored; the container uses a volume)
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

Login validates against `users.password_hash`; hashing is stdlib pbkdf2 in
`app/security.py`. The seed creates `user` / `password`.

## Database

SQLite through SQLAlchemy 2.0 ORM. `docs/DATABASE.md` is the reference for the schema,
ordering and cascade rules; read it before changing anything here.

`db.configure(path)` builds the engine and session factory and registers the
`PRAGMA foreign_keys=ON` connect listener that SQLite needs for `ON DELETE CASCADE`. It
runs at import with `settings.database_path`, and again from the pytest fixture to point at
a temporary file. `init_db()` runs in the app lifespan: create the tables, then seed once.

Routes take `Db = Annotated[Session, Depends(get_db)]`. They resolve rows through
`load_board` / `load_column` / `load_card`, which scope to the session user and raise 404
for anything belonging to someone else. Positions are rewritten densely by `renumber` on
every ordering change.

There are no migrations. A schema change during the MVP means deleting `backend/data/pm.db`
locally, or `docker volume rm pm-data` for the container, and letting it reseed.

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

Anything touching the database uses the `client` fixture from `tests/conftest.py`, which
points the app at a `tmp_path` database, or `signed_in`, which is the same client already
logged in. Use them rather than a module-level `TestClient`: the fixture enters the app
lifespan, and outside it no database exists and nothing is seeded.

To run them in the container: `docker exec pm-app pytest`.

Ruff is the linter and formatter. Run both before committing Python changes:

```
uv run ruff check .      # add --fix to apply safe fixes
uv run ruff format .
```

Rules selected: `E`, `F`, `I`, `UP`, `B` (pycodestyle, pyflakes, isort, pyupgrade,
bugbear). Keep imports sorted by ruff rather than by hand.

## Not built yet

The AI routes land in Parts 8 and 9 of `docs/PLAN.md`. `messages` exists in the schema but
nothing reads or writes it yet.
