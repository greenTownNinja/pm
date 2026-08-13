# Frontend

Next.js 16 (App Router) + React 19 + Tailwind CSS 4 + TypeScript. Built as a static
export and served by FastAPI at `/`. Sign in goes through the API; the board itself is
still client-only state, lost on reload. Parts 7 and 10 of `docs/PLAN.md` connect the board
and the chat to the backend.

## Layout

```
src/app/          layout.tsx (fonts, metadata), page.tsx (renders AppShell), globals.css
src/app/fonts/    vendored woff2 files, loaded via next/font/local
src/components/   AppShell, LoginForm, KanbanBoard, KanbanColumn, KanbanCard,
                  KanbanCardPreview, NewCardForm
src/lib/          kanban.ts - types, seed data, move logic, id generation
                  api.ts - typed fetch wrappers for /api
src/test/         vitest setup
scripts/          copy-export.mjs - copies out/ into backend/static/
tests/            playwright e2e specs, helpers.ts (signIn)
```

## Auth

`AppShell` (`"use client"`) is the only thing `page.tsx` renders. It calls `me()` on mount
and shows a loading state, then either `LoginForm` or `KanbanBoard`. Signing out calls
`logout()` and drops back to the form. `KanbanBoard` takes `username` and `onSignOut` and
renders the sign-out control in its header; it knows nothing else about auth.

`src/lib/api.ts` wraps `fetch` with `credentials: "include"` so the session cookie travels,
and throws the API's `detail` message on a non-2xx. `me()` is the exception: it returns
`null` on 401 rather than throwing, since "not signed in" is a normal state. Part 7 adds
the board routes to this module.

## Data model

Defined in `src/lib/kanban.ts` and shared with the backend API:

```ts
type Card = { id: string; title: string; details: string };
type Column = { id: string; title: string; cardIds: string[] };
type BoardData = { columns: Column[]; cards: Record<string, Card> };
```

Cards are stored in a flat `cards` map; each column holds an ordered `cardIds` array. The
backend API returns and accepts this exact shape - keep them in sync.

`initialData` seeds five columns (Backlog, Discovery, In Progress, Review, Done) with eight
cards. From Part 7 it is test-only data, not a runtime source.

`moveCard(columns, activeId, overId)` is the pure reorder function, covering both
within-column reordering and cross-column moves. `overId` may be a card id (insert at that
card's index) or a column id (append to the end). It returns the original array unchanged
when the ids do not resolve. Unit tested in `src/lib/kanban.test.ts`.

`createId(prefix)` makes client-side ids. From Part 7 card ids come from the server.

## Components

**`KanbanBoard`** (`"use client"`) takes `username` / `onSignOut` and owns all board state
and every handler:
`handleDragStart` / `handleDragEnd`, `handleRenameColumn`, `handleAddCard`,
`handleDeleteCard`. It sets up `DndContext` with a `PointerSensor` (6px activation
distance) and `closestCorners` collision detection, and renders a `DragOverlay`.
It also renders the page header.

**`KanbanColumn`** is a dnd-kit droppable wrapping a `SortableContext`. The column title is
a borderless `<input>` (`aria-label="Column title"`) that renames on every keystroke -
Part 7 debounces this before it hits the API. Renders `data-testid="column-{id}"`,
an empty-state placeholder, and `NewCardForm` at the bottom.

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

`playwright.config.ts` builds the export and starts uvicorn on port 8000, matching the
container. `reuseExistingServer` is on, so **stop the `pm-app` container before running the
e2e suite** or the tests silently run against the image instead of the working tree.

## Build

`next.config.ts` sets `output: "export"`, producing a static `out/` directory that FastAPI
serves at `/`. Consequences: no SSR, no server actions, no Next route handlers, and images
must be unoptimized. From Part 7 all data goes through `/api` with
`credentials: "include"` so the session cookie is sent.

- `npm run build` - writes `out/`.
- `npm run build:static` - build, then copy `out/` into `backend/static/` for local runs.
  `backend/static/` is gitignored apart from `.gitkeep`.

The Docker build does the same thing across stages: a `node` stage runs `npm ci` and
`npm run build`, and the Python stage copies `out/` to `/app/static`.
