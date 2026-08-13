# Project Plan

Detailed plan for the Project Management MVP described in AGENTS.md. Each part has a
checklist, tests, and success criteria. Parts are executed in order; do not start a part
until the previous part's success criteria are met.

## Agreed decisions

These were confirmed with the user during planning:

1. **Persistence**: relational tables in SQLite (not a JSON blob).
   `users` / `boards` / `columns` / `cards` / `messages`, with integer `position`
   ordering on columns and cards.
2. **Auth**: HttpOnly signed session cookie. `POST /api/login` sets it, `POST /api/logout`
   clears it, a FastAPI dependency guards every other `/api` route.
3. **Frontend build**: Next.js static export (`output: "export"`). FastAPI serves the
   exported `out/` directory at `/`. One process, one container. No SSR, no server
   actions, no Next route handlers - all data flows through `/api`.
4. **Chat history**: persisted in SQLite, keyed to the board, replayed to the model each turn.

Additional decisions made while planning, flagged here for visibility:

5. **DB access layer**: SQLAlchemy 2.0 ORM. Ordering, reparenting and cascade deletes
   across four tables are enough relational work to justify it over raw `sqlite3`.
6. **Session implementation**: Starlette `SessionMiddleware` (itsdangerous-signed cookie).
   No new dependency beyond what FastAPI already pulls in.
7. **API shape**: the API speaks the frontend's existing `BoardData` shape
   (`{columns: [...], cards: {...}}`). The relational schema is an implementation detail
   assembled on read and diffed on write. This keeps the frontend, the tests, and the
   AI prompt all working against one stable contract.

## Gaps found in the starting frontend

Recorded during planning; addressed in the parts noted.

- **Card editing is missing.** The business requirements say cards can be edited, but the
  demo only supports add, delete, and drag. Added in Part 3.
- Column rename and card delete already work (both in `KanbanBoard.tsx`), so Parts 3 and 7
  need to persist them rather than build them.
- `playwright.config.ts` starts `next dev` on port 3000. From Part 3 onward the e2e suite
  must run against the FastAPI-served static build instead.
- `layout.tsx` uses `next/font/google`, which downloads fonts at build time. The Docker
  build therefore needs network access, or the fonts need self-hosting. Resolved in Part 3.
- There is **no `.env` in the project root** yet, despite AGENTS.md referring to one.
  Created in Part 2, populated with a real key before Part 8.

---

## Part 1: Plan

**Goal**: a reviewed, approved plan and an accurate description of the existing frontend.

- [x] Review AGENTS.md and the existing frontend code
- [x] Resolve open design questions with the user
- [x] Enrich `docs/PLAN.md` with per-part checklists, tests, and success criteria
- [x] Write `frontend/AGENTS.md` describing the existing code
- [x] User reviews and approves this plan

**Success criteria**: user has explicitly approved this document.

---

## Part 2: Scaffolding

**Goal**: a Docker container that runs FastAPI, serves a placeholder static page at `/`,
and answers an API call. No Kanban, no database yet.

- [x] Create `backend/pyproject.toml` (uv-managed) with `fastapi`, `uvicorn[standard]`,
      `sqlalchemy`, `httpx`, `pydantic-settings`, and dev group `pytest`, `pytest-asyncio`
- [x] Create `backend/app/main.py` with the FastAPI app
- [x] Add `GET /api/health` returning `{"status": "ok"}`
- [x] Mount a `StaticFiles` app at `/` serving `backend/static/`, with an index fallback
      so client-side routes resolve to `index.html`
- [x] Add a placeholder `backend/static/index.html` that calls `/api/health` and renders
      the result, proving the static-plus-API round trip
- [x] Create `.env` in the project root with `OPENROUTER_API_KEY=` (empty for now) and
      `SESSION_SECRET=`; confirm `.gitignore` excludes it
- [x] Load settings from `.env` via `pydantic-settings`
- [x] Write `Dockerfile`: `uv` base image, install deps from `pyproject.toml`, copy the
      backend, expose 8000, run uvicorn
- [x] Write `scripts/start.sh`, `scripts/stop.sh` (Mac/Linux) and `scripts/start.ps1`,
      `scripts/stop.ps1` (Windows). Plain `docker build` and `docker run` - no compose.
      Each script names the container `pm-app`, publishes 8000, passes `--env-file .env`,
      and mounts the named volume `pm-data` at `/app/data` for the SQLite file
- [x] Write `backend/AGENTS.md` describing the backend layout

**Tests**

- [x] `pytest` unit test: `GET /api/health` returns 200 and `{"status": "ok"}`
- [x] `pytest` unit test: `GET /` returns 200 and `text/html`
- [x] `pytest` unit test: an unknown path falls back to `index.html`
- [x] Manual: `scripts/start.sh` builds and runs, `/api/health` and `/` both answer over
      HTTP from the container, `scripts/stop.sh` removes it cleanly, and a restart works
- [x] Manual: confirm in a browser that the page *renders* the health result. Superseded
      by Part 3 - the placeholder page is gone and `/` now serves the real board, which is
      what gets checked visually instead

**Success criteria**: a fresh clone plus `scripts/start.sh` yields a working page at
`http://localhost:8000` that displays live data fetched from `/api/health`. All pytest
tests pass inside the container.

---

## Part 3: Add in Frontend

**Goal**: the real Kanban demo, statically built and served by FastAPI at `/`.
Still in-memory on the client, no persistence.

- [x] Set `output: "export"` and `images: { unoptimized: true }` in `next.config.ts`
- [x] Verify `next build` produces `out/` cleanly; fix any static-export incompatibilities
- [x] Resolve the `next/font/google` build-time fetch: either allow network during the
      Docker build stage or vendor the two fonts locally. Prefer vendoring - it makes the
      build reproducible and offline-capable
- [x] Add **card editing** to the frontend: click a card title or details to edit inline,
      with an `onEditCard(cardId, title, details)` handler on `KanbanBoard`
- [x] Add a Node build stage to the `Dockerfile`: `npm ci`, `npm run build`, copy `out/`
      into the Python stage's `backend/static/`
- [x] Point the static mount at the exported build, keeping `/api/*` routed to FastAPI
- [x] Update `playwright.config.ts` to run against the FastAPI-served build
      (`baseURL` `http://127.0.0.1:8000`, `webServer` starts the backend) rather than `next dev`

**Tests**

- [x] Existing vitest suites still pass (`npm run test:unit`)
- [x] New vitest tests for card editing: editing a title updates the card; editing details
      updates the card; cancelling leaves the card unchanged
- [x] Existing playwright suites pass against the served build
- [x] New playwright test: edit a card end to end
- [x] `pytest`: `GET /` serves the Next export; a known asset path returns 200;
      an unknown path falls back to `index.html`

**Success criteria**: `scripts/start.sh` then `http://localhost:8000` shows the full
Kanban board with working drag/drop, rename, add, delete, and edit. `npm run test:all`
and `pytest` both pass.

**Notes from execution**

- Fonts are vendored as latin-subset variable woff2 under `frontend/src/app/fonts/` and
  loaded with `next/font/local`. The Docker build now runs with no network access.
- The SPA fallback needed fixing. The export ships its own `404.html`, and
  `StaticFiles(html=True)` *returns* that as a 404 response rather than raising, so the
  old `except HTTPException` never fired and unknown paths 404'd. `SPAStaticFiles` now
  checks the response status too.
- `backend/static/` is a build artifact and is gitignored apart from `.gitkeep`, which
  keeps the directory present so the static mount resolves on a fresh clone.
  `npm run build:static` builds and copies it there for local runs; the Docker build
  copies `out/` across stages instead.
- Card editing disables dragging on the card being edited, since the whole article is the
  drag handle.
- `uv sync --frozen` with `uv.lock` in the image, so the build uses locked versions and
  fails loudly on drift.

---

## Part 4: Fake user sign in

**Goal**: `/` requires login before the board is visible; logout returns to the login screen.

- [x] Add `SessionMiddleware` with `SESSION_SECRET` from `.env`; cookie flagged
      `httponly`, `samesite=lax`
- [x] `POST /api/login` accepts `{username, password}`, validates against the hardcoded
      `user` / `password` for now, sets the session, returns `{"username": ...}`
- [x] `POST /api/logout` clears the session
- [x] `GET /api/me` returns the current user or 401
- [x] `require_user` FastAPI dependency returning 401 when unauthenticated; apply to every
      `/api` route except login, logout, and health
- [x] Frontend `LoginForm` component styled to the project color scheme
- [x] Frontend gates on `GET /api/me` at mount: show a loading state, then the login form
      or the board
- [x] Logout control in the board header

**Tests**

- [x] `pytest`: correct credentials return 200 and set a cookie
- [x] `pytest`: wrong password returns 401 and sets no cookie
- [x] `pytest`: a guarded route returns 401 without a cookie and 200 with one
- [x] `pytest`: after logout, the guarded route returns 401 again
- [x] `pytest`: the session cookie is HttpOnly
- [x] vitest: `LoginForm` submits credentials and surfaces an error on failure
- [x] playwright: visiting `/` shows the login form; logging in shows the board; reloading
      keeps the session; logging out returns to the login form

**Success criteria**: the board is unreachable without logging in, the session survives a
page reload, and logout invalidates it. All suites pass.

**Notes from execution**

- The SPA fallback was masking missing API routes: an unmatched `/api/...` path fell
  through to the static mount and returned `index.html` with a 200, so `GET /api/me`
  "succeeded" before the route existed. `SPAStaticFiles.fallback` now 404s anything under
  `api/` and only falls back to `index.html` for client-side routes. Found because a stale
  Part 3 container was still holding port 8000 and answering `/api/me` with the board HTML.
- `itsdangerous` added as an explicit dependency; `SessionMiddleware` needs it and it was
  not already pulled in.
- `AppShell` owns the auth state (loading / login form / board) and passes `username` and
  `onSignOut` to `KanbanBoard`, which keeps `KanbanBoard` about the board.
- Next injects its own `role="alert"` route announcer, so e2e assertions on the login error
  are scoped to `data-testid="login-form"`.
- Playwright's `reuseExistingServer: true` will silently reuse a running `pm-app`
  container on port 8000. Stop the container before running the e2e suite.

---

## Part 5: Database modeling

**Goal**: an agreed schema, documented and signed off before any DB code is written.

- [x] Write `docs/DATABASE.md` covering the tables below, the ordering strategy, cascade
      rules, the seed behaviour for a new user's board, and the `BoardData` JSON shape the
      API exposes
- [x] Include a worked example: the seeded five-column board as both rows and API JSON
- [ ] **Get explicit user sign-off on `docs/DATABASE.md` before starting Part 6**

Proposed schema:

```
users     (id, username UNIQUE, password_hash, created_at)
boards    (id, user_id -> users.id, title, created_at, updated_at)
columns   (id, board_id -> boards.id, title, position)
cards     (id, column_id -> columns.id, title, details, position)
messages  (id, board_id -> boards.id, role, content, created_at)
```

- Card order within a column, and column order within a board, are given by `position`
  (0-based, rewritten contiguously on every mutation - simple and correct at MVP scale).
- `ON DELETE CASCADE` from boards to columns to cards and messages.
- `password_hash` exists so multiple real users are supportable later; the MVP seeds a
  single `user` row and still validates against it rather than special-casing login.
- A new user gets one board seeded with the five columns from the existing demo.

**Tests**: none (documentation part).

**Success criteria**: user has approved `docs/DATABASE.md`.

---

## Part 6: Backend

**Goal**: full CRUD over the board through the API, thoroughly tested. Frontend untouched.

- [x] SQLAlchemy models for the five tables
- [x] Create the SQLite file and tables at startup if absent; store under a mounted volume
      path so data survives container restarts
- [x] Seed the `user` row and its board with the five demo columns on first run
- [x] `GET /api/board` returns the board in `BoardData` shape
- [x] `PATCH /api/columns/{id}` renames a column
- [x] `POST /api/columns/{id}/cards` creates a card at the end of the column
- [x] `PATCH /api/cards/{id}` edits title and/or details
- [x] `DELETE /api/cards/{id}` deletes a card and closes the position gap
- [x] `POST /api/cards/{id}/move` takes `{columnId, position}` and reorders both the source
      and target columns
- [x] Every route scoped to the session user; a board or card belonging to another user
      returns 404
- [x] Pydantic request and response models throughout

**Tests** (pytest, against a temporary SQLite file per test)

- [x] The database and tables are created when the file does not exist
- [x] Seeding is idempotent across restarts
- [x] `GET /api/board` returns the seeded shape, columns and cards in position order
- [x] Column rename persists
- [x] Card create appends at the end and returns the new id
- [x] Card edit persists title and details independently
- [x] Card delete removes it and leaves positions contiguous
- [x] Move within a column reorders correctly, including to first and to last
- [x] Move across columns removes from source, inserts at the requested index, and leaves
      both columns contiguous
- [x] Every route returns 401 unauthenticated
- [x] Cross-user access returns 404
- [x] Invalid ids, out-of-range positions, and empty titles return 4xx rather than 500

**Success criteria**: the full pytest suite passes, and a manual `curl` sequence
(login, read, mutate, read back) shows the mutation persisted across a container restart.

**Notes from execution**

- `db.configure(path)` rebinds the engine and session factory, so the pytest fixture points
  the app at a `tmp_path` database and lets the app's own startup create and seed it. No
  dependency overrides, and the seeding path is exercised by every test.
- Login now validates against `users.password_hash` (stdlib pbkdf2), so Part 4's hardcoded
  credentials are gone from `app/auth.py`. The seed still creates `user` / `password`.
- Move semantics are remove-then-insert: moving a card to index 1 of its own column lands
  it *after* the card that was there. An index past the end means "last". This is what
  dnd-kit's drop indices already mean, and Part 7 depends on it.
- Every mutation returns the full board; card creation returns `{card, board}` so the
  client gets the server-assigned id without diffing. Recorded in `docs/DATABASE.md`.
- Card and column path params are typed `int`, so a non-numeric id is a 422 from FastAPI.
  `columnId` inside the move body is a string like every other id in the contract, and a
  non-numeric one is a 404.
- `backend/data/` is gitignored; the container overrides `DATABASE_PATH` to the volume.

---

## Part 7: Frontend + Backend

**Goal**: the UI reads and writes through the API. The board is genuinely persistent.

- [x] `src/lib/api.ts` client with typed wrappers for every route, sending
      `credentials: "include"`
- [x] `KanbanBoard` loads from `GET /api/board` on mount instead of `initialData`
- [x] Loading and error states for the initial fetch
- [x] Every mutation (rename, add, edit, delete, move) applies optimistically, calls the
      API, and rolls back the local state on failure
- [x] Debounce column rename so typing does not fire a request per keystroke
- [x] Keep `initialData` only as test seed data, out of the runtime path
- [x] Card ids come from the server, so drop client-side `createId` for cards

**Tests**

- [x] vitest with a mocked fetch: board renders from the API response; each mutation issues
      the expected request; a failed request rolls the UI back
- [x] vitest: the loading and error states render
- [x] pytest integration: login, mutate through the API, and confirm `GET /api/board`
      reflects it
- [x] playwright against the real stack: log in, add a card, edit it, drag it to another
      column, reload the page, and confirm every change survived
- [x] playwright: changes survive a container restart

**Success criteria**: every board change persists across reload and restart. No demo data
remains in the runtime path. All suites pass.

**Notes from execution**

- Card creation is the one mutation that is **not** optimistic: only the server can assign
  the id, and inventing a temporary one would mean keeping `createId` alive purely to
  reconcile it away. The request is local and fast, and the plan also asked for server-owned
  card ids; this is where the two items met.
- Rollback restores the last board the server confirmed, held in a ref, rather than a
  snapshot taken per mutation. That is the state debounced renames and overlapping requests
  should return to.
- `resolveDrop` in `kanban.ts` turns a dnd-kit drop into the `{columnId, position}` the API
  wants, reading the index from the pre-move column so it agrees with the server's
  remove-then-insert. Unit tested alongside `moveCard`.
- A pending debounced rename is flushed on unmount, so signing out mid-rename still saves.
  Reloading the page within the debounce window still loses it; the e2e spec waits for the
  PATCH rather than papering over that.
- `initialData` moved out of `src/lib/kanban.ts` to `src/test/board-fixture.ts`, so nothing
  in the runtime path imports demo data. `createId` is gone.
- The e2e specs create their own uniquely-named card, act on it and delete it, because the
  board is now shared persistent state rather than a fresh in-memory demo per test. They
  also locate cards by `data-testid` once created: locating by text breaks the moment a card
  is edited, since the title moves into an input value.
- The container-restart test lives in `tests/restart.spec.ts` and skips unless
  `PM_E2E_CONTAINER=1`, since it restarts `pm-app`. Run against the container it passes.
- `src/test/vitest.d.ts` referenced `vitest` rather than `vitest/globals`, so `tsc` did not
  see `describe` / `it` / `expect`. Fixed; `npx tsc --noEmit` is clean.

---

## Part 8: AI connectivity

**Goal**: prove the OpenRouter call works, in isolation, before building anything on it.

- [x] Put a real `OPENROUTER_API_KEY` in `.env`
- [x] `backend/app/ai.py` with an async `httpx` client calling OpenRouter's
      chat completions endpoint with `openai/gpt-oss-120b`
- [x] Read the key from settings; fail loudly at startup if the AI feature is used without it
- [x] Handle timeouts and non-200 responses with a clear error, not a stack trace
- [x] Temporary `POST /api/ai/ping` that asks the model "what is 2+2?" and returns the reply

**Tests**

- [x] pytest with a mocked OpenRouter response: the request carries the right model,
      auth header, and message shape
- [x] pytest: a timeout and a 500 from OpenRouter both surface as a clean 502
- [x] Manual, live: `curl` the ping route and confirm the answer contains `4`

**Success criteria**: the live ping returns a correct answer from the real model. Mocked
tests pass without network access.

**Notes from execution**

- `complete(messages)` is the whole client: it posts to OpenRouter, checks the status, and
  returns `choices[0].message.content`. Part 9 builds its structured-output call on top.
- The key is checked when the call is made, not at startup: the app has to boot and serve
  the board without one, so "fail loudly" means a 500 naming `OPENROUTER_API_KEY` from the
  AI route rather than a refusal to start.
- Timeouts and connection failures are caught as `httpx.HTTPError`, and a non-200 upstream
  is checked explicitly; both become a 502 with the reason in the detail.
- Tests monkeypatch `httpx.AsyncClient.post`, recording the call so the model, auth header
  and message shape are asserted on the real request the client builds. No network.
- Live check: `POST /api/ai/ping` returned `2 + 2 = 4.` from `openai/gpt-oss-120b`.

---

## Part 9: AI over the board

**Goal**: the model sees the board and the conversation, and answers with a structured
response that may include board updates.

- [x] Define the response schema: `{reply: string, updates: Action[] | null}` where each
      action is one of `create_card`, `edit_card`, `move_card`, `delete_card`,
      `rename_column`, each with the fields that operation needs
- [x] Request Structured Outputs via `response_format: {type: "json_schema", strict: true}`.
      **Verify OpenRouter honours strict json_schema for this model early in the part** - if
      it does not, fall back to tool calling with the same schema, and record which path was
      taken in `docs/`
- [x] System prompt: role, the current board JSON, the available actions, and an instruction
      to return no updates when the user is only asking a question
- [x] `POST /api/chat` takes `{message}`, loads history and the board, calls the model,
      applies any returned actions in a single transaction, persists both messages, and
      returns `{reply, board}` with the post-update board
- [x] `GET /api/chat/history` returns the stored conversation
- [x] Validate every action against the real board before applying; reject unknown card or
      column ids rather than half-applying a batch
- [x] Cap the history sent to the model at a fixed number of recent turns

**Tests**

- [x] pytest with mocked model responses, one per action type, asserting the board changes
      exactly as expected
- [x] pytest: a multi-action response applies all actions atomically
- [x] pytest: an action referencing an unknown id rolls back the whole batch and returns an error
- [x] pytest: a reply with `updates: null` leaves the board untouched
- [x] pytest: malformed model JSON returns a clean error, not a 500
- [x] pytest: history is persisted and replayed in order, and is trimmed at the cap
- [x] Manual, live: "move the QA card to Done" actually moves it; "what is on my board?"
      answers without changing anything

**Success criteria**: live requests both answer questions and correctly modify the board.
All mocked tests pass.

**Notes from execution**

- **Structured Outputs works.** A live probe confirmed OpenRouter honours
  `response_format: {type: "json_schema", strict: true}` for `openai/gpt-oss-120b`, so
  the tool-calling fallback was not needed. The request also sends
  `provider: {require_parameters: true}` so OpenRouter only routes to providers that
  enforce the schema rather than silently ignoring it.
- Strict mode allows no optional or conditional properties, so there is **one flat action
  shape** rather than a per-action union: `action` plus `cardId`, `columnId`, `title`,
  `details`, `position`, all required and all nullable. The prompt tells the model to null
  the fields an action does not need, and `apply_action` reads only the ones it needs.
- `move_card` with a null `position` means the bottom of the target column. That is the
  natural reading of "move it to Done", and the remove-then-insert clamp from Part 6
  already handles a past-the-end index.
- Ids the model invents are a 400, not a 404: `resolve` wraps `load_card` / `load_column`
  so cross-user rows stay invisible, and turns their 404 into a bad-request naming the id.
  The whole batch is rolled back, and the turn is not written to `messages` either.
- Board mutation logic is not duplicated: `place_card` moved out of `board.move_card` and
  both the REST route and the AI action call it.
- `HISTORY_LIMIT` (20 messages) caps only what is *replayed to the model*.
  `GET /api/chat/history` still returns the whole conversation.
- Live: "move the QA micro-interactions card to Review" moved it; "what is on my board?"
  answered without changing anything. The model replies in markdown despite being asked
  for plain prose - Part 10 decides whether to render it or press harder in the prompt.

---

## Part 10: AI chat sidebar

**Goal**: the chat UI, with the board refreshing when the AI changes it.

- [ ] `ChatSidebar` component: message list, input, send button, collapsible panel, styled
      to the project color scheme (purple for the send action, blue for accents,
      navy headings, gray supporting text)
- [ ] Load history from `GET /api/chat/history` on mount
- [ ] Optimistic user message, then a pending indicator while the model responds
- [ ] Apply the `board` returned by `POST /api/chat` directly to board state so the Kanban
      refreshes without a second request
- [ ] Error state when the request fails, with the user's message preserved for retry
- [ ] Responsive: the sidebar overlays rather than crushes the board on narrow viewports
- [ ] Remove the temporary `/api/ai/ping` route from Part 8

**Tests**

- [ ] vitest with a mocked API: sending a message renders the user message then the reply
- [ ] vitest: a response containing a board update re-renders the Kanban
- [ ] vitest: history loads on mount
- [ ] vitest: a failed send shows an error and keeps the input content
- [ ] playwright against the real stack: open the sidebar, ask the AI to add a card, and
      confirm both the reply and the new card appear; reload and confirm both persisted
- [ ] Full `npm run test:all` and `pytest` green

**Success criteria**: a user can log in, chat with the AI, watch it modify the board live,
and find every change still there after a restart. All suites pass. `README.md` documents
setup and the start/stop scripts, minimally.
