# Frontend

Next.js 16 (App Router) + React 19 + Tailwind CSS 4 + TypeScript. Built as a static
export and served by FastAPI at `/`. Sign in and the whole board go through the API, so
everything on screen is persisted. Part 10 of `docs/PLAN.md` adds the chat sidebar.

## Layout

```
src/app/          layout.tsx (fonts, metadata), page.tsx (renders AppShell), globals.css
src/app/fonts/    vendored woff2 files, loaded via next/font/local
src/components/   AppShell, LoginForm, KanbanBoard, KanbanColumn, KanbanCard,
                  KanbanCardPreview, NewCardForm
src/lib/          kanban.ts - types, move logic, drop resolution
                  api.ts - typed fetch wrappers for /api
src/test/         vitest setup, board-fixture.ts (demo board, tests only)
scripts/          copy-export.mjs - copies out/ into backend/static/
tests/            playwright e2e specs, helpers.ts (signIn, addCard, deleteCard)
```

## Auth

`AppShell` (`"use client"`) is the only thing `page.tsx` renders. It calls `me()` on mount
and shows a loading state, then either `LoginForm` or `KanbanBoard`. Signing out calls
`logout()` and drops back to the form. `KanbanBoard` takes `username` and `onSignOut` and
renders the sign-out control in its header; it knows nothing else about auth.

`src/lib/api.ts` wraps `fetch` with `credentials: "include"` so the session cookie travels,
and throws the API's `detail` message on a non-2xx. `me()` is the exception: it returns
`null` on 401 rather than throwing, since "not signed in" is a normal state.

## Talking to the API

`src/lib/api.ts` is the only place that calls `fetch`. Components never build URLs.

Every board mutation resolves to the whole board, so the client reconciles in one step;
`createCard` also returns the new card, since only the server knows its id. Ids are opaque
strings that round-trip untouched.

## Data model

Defined in `src/lib/kanban.ts` and shared with the backend API:

```ts
type Card = { id: string; title: string; details: string };
type Column = { id: string; title: string; cardIds: string[] };
type BoardData = { columns: Column[]; cards: Record<string, Card> };
```

Cards are stored in a flat `cards` map; each column holds an ordered `cardIds` array. The
backend API returns and accepts this exact shape - keep them in sync.

`moveCard(columns, activeId, overId)` is the pure reorder function, covering both
within-column reordering and cross-column moves. `overId` may be a card id (insert at that
card's index) or a column id (append to the end). It returns the original array unchanged
when the ids do not resolve. Unit tested in `src/lib/kanban.test.ts`.

`resolveDrop(columns, activeId, overId)` expresses that same drop as the
`{columnId, position}` the API takes. It reads the index from the **pre-move** column,
because the server removes the card before inserting it and so does `moveCard`. Change one
and you must change the other.

The demo board lives in `src/test/board-fixture.ts` as `boardFixture`. It is test data
only; nothing in the runtime path imports it, and card ids come from the server.

## Components

**`KanbanBoard`** (`"use client"`) takes `username` / `onSignOut`, loads the board from
`GET /api/board` on mount, and owns every handler: `handleDragStart` / `handleDragEnd`,
`handleRenameColumn`, `handleAddCard`, `handleEditCard`, `handleDeleteCard`. It sets up
`DndContext` with a `PointerSensor` (6px activation distance) and `closestCorners`
collision detection, and renders a `DragOverlay`. It also renders the page header.

How it saves:

- Rename, edit, delete and move apply **optimistically**, then call the API. On failure the
  board reverts to `confirmed.current`, the last board the server acknowledged, and an
  error banner appears in the header.
- Adding a card is **not** optimistic - the server assigns the id, so the returned board is
  applied when it arrives.
- Column rename is debounced by `RENAME_DEBOUNCE_MS` (400ms) per column, since the input
  fires on every keystroke. Anything still pending is flushed on unmount, so signing out
  mid-rename does not lose it.
- `load` sets state only from promise callbacks. Setting it synchronously in the mount
  effect trips `react-hooks/set-state-in-effect`.

**`KanbanColumn`** is a dnd-kit droppable wrapping a `SortableContext`. The column title is
a borderless `<input>` (`aria-label="Column title"`) that renames on every keystroke.
Renders `data-testid="column-{id}"`, an empty-state placeholder, and `NewCardForm` at the
bottom.

**`KanbanCard`** is the sortable card. The whole article is the drag handle, so any
interactive control inside it needs care. Renders `data-testid="card-{id}"` and a Remove
button labelled `Delete {title}`. Clicking the title/details block (a button labelled
`Edit {title}`) opens an inline editor with `Edit title` / `Edit details` fields and
Save card / Cancel. Sorting is disabled while editing, and the drag listeners are not
spread onto the article, so the form is usable.

**`KanbanCardPreview`** is the non-interactive card rendered inside the `DragOverlay`.

**`NewCardForm`** toggles between an "Add a card" button and a title/details form.

## Styling

Tailwind 4 via `@import "tailwindcss"` in `globals.css`. The project palette is exposed as
CSS custom properties on `:root` and consumed as `text-[var(--navy-dark)]` and similar -
follow that pattern rather than hardcoding hex values.

`--accent-yellow` `#ecad0a`, `--primary-blue` `#209dd7`, `--secondary-purple` `#753991`,
`--navy-dark` `#032147`, `--gray-text` `#888888`, plus `--surface`, `--surface-strong`,
`--stroke`, `--shadow`.

Fonts are Space Grotesk (display, `.font-display`) and Manrope (body). They are vendored
as latin-subset variable woff2 files in `src/app/fonts/` and loaded with
`next/font/local`, so `next build` needs no network access. See `src/app/fonts/README.md`.

## Testing

- `npm run test:unit` - vitest + Testing Library, jsdom, `globals: true` (no imports needed
  for `describe` / `it` / `expect`), `@` aliased to `src`. Only matches `src/**/*.test.*`.
- `npm run test:e2e` - playwright, chromium only. Drag/drop is exercised with real
  `page.mouse` movements in steps, because dnd-kit ignores instantaneous jumps. Every board
  spec signs in first via `tests/helpers.ts`. Assertions on the login error are scoped to
  `data-testid="login-form"`, because Next renders its own `role="alert"` route announcer.
- `npm run test:all` - both.

The e2e suite runs against a persistent board, so specs create their own uniquely-named
card, act on it, and delete it rather than touching the seeded cards. `addCard` returns a
locator keyed on the card's `data-testid`: locating by text stops matching as soon as the
card is edited, because the title moves into an input value.

`tests/restart.spec.ts` restarts the container and skips unless `PM_E2E_CONTAINER=1`. Run
it with a `pm-app` container up: `PM_E2E_CONTAINER=1 npx playwright test restart`.

`playwright.config.ts` builds the export and starts uvicorn on port 8000, matching the
container. `reuseExistingServer` is on, so **stop the `pm-app` container before running the
e2e suite** or the tests silently run against the image instead of the working tree.

## Build

`next.config.ts` sets `output: "export"`, producing a static `out/` directory that FastAPI
serves at `/`. Consequences: no SSR, no server actions, no Next route handlers, and images
must be unoptimized. All data goes through `/api` with
`credentials: "include"` so the session cookie is sent.

- `npm run build` - writes `out/`.
- `npm run build:static` - build, then copy `out/` into `backend/static/` for local runs.
  `backend/static/` is gitignored apart from `.gitkeep`.

The Docker build does the same thing across stages: a `node` stage runs `npm ci` and
`npm run build`, and the Python stage copies `out/` to `/app/static`.
