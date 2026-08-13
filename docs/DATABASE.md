# Database

The schema for the Project Management MVP. Written in Part 5 of `docs/PLAN.md` and
implemented in Part 6. SQLite, accessed through SQLAlchemy 2.0 ORM.

## File location

One SQLite file, path from `settings.database_path`:

- container: `/app/data/pm.db` - `/app/data` is the named volume `pm-data`, so data
  survives `docker rm`
- local runs: `backend/data/pm.db`, gitignored

Created with its tables on startup if absent, per the business requirement.

`PRAGMA foreign_keys=ON` is issued on every connection through a SQLAlchemy `connect`
event listener. SQLite ignores foreign keys, and therefore `ON DELETE CASCADE`, unless
that pragma is set per connection.

## Tables

```
users
  id             INTEGER PK
  username       TEXT NOT NULL UNIQUE
  password_hash  TEXT NOT NULL
  created_at     DATETIME NOT NULL

boards
  id             INTEGER PK
  user_id        INTEGER NOT NULL -> users.id     ON DELETE CASCADE
  title          TEXT NOT NULL
  created_at     DATETIME NOT NULL
  updated_at     DATETIME NOT NULL

columns
  id             INTEGER PK
  board_id       INTEGER NOT NULL -> boards.id    ON DELETE CASCADE
  title          TEXT NOT NULL
  position       INTEGER NOT NULL

cards
  id             INTEGER PK
  column_id      INTEGER NOT NULL -> columns.id   ON DELETE CASCADE
  title          TEXT NOT NULL
  details        TEXT NOT NULL DEFAULT ''
  position       INTEGER NOT NULL

messages
  id             INTEGER PK
  board_id       INTEGER NOT NULL -> boards.id    ON DELETE CASCADE
  role           TEXT NOT NULL          -- 'user' or 'assistant'
  content        TEXT NOT NULL
  created_at     DATETIME NOT NULL
```

Indexes: `columns.board_id`, `cards.column_id`, `messages.board_id`. Every list read is
"all rows for this parent, ordered by position", so those cover the query load.

`column` is a reserved word in SQL. The table is named `columns`, which is fine, but the
SQLAlchemy class is `BoardColumn` to avoid colliding with `sqlalchemy.Column`.

### Notes on individual fields

- **`users.password_hash`** exists so multiple real users are supportable later. The MVP
  seeds one `user` row and login validates against the stored hash rather than
  special-casing the hardcoded pair, so nothing about the login path changes when real
  users arrive. Hashing is `hashlib.pbkdf2_hmac("sha256", ...)` from the standard library,
  stored as `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`. No new dependency.
  Part 4's hardcoded constants in `app/auth.py` are removed when this lands.
- **`boards.updated_at`** is touched on every mutation. Nothing reads it yet; it is there
  because a board without one is annoying to debug.
- **`cards.details`** defaults to the empty string rather than being nullable, so the API
  never has to decide between `null` and `""`.
- **`messages.role`** is a plain text column, not an enum. Two values, checked in Python.

## Ordering

`position` is 0-based and contiguous within its parent: columns within a board, cards
within a column. Every mutation that changes an order rewrites the affected positions as a
dense `0..n-1` sequence in the same transaction.

This is the simple, obviously-correct option at MVP scale (five columns, a handful of
cards). It rewrites more rows than a gap-based or fractional scheme would, and that is
fine here.

There is deliberately **no unique constraint on `(board_id, position)` or
`(column_id, position)`**. Renumbering passes through intermediate states where two rows
briefly share a position, and a unique index would reject them without a deferred-constraint
dance that SQLite does not support.

Reads sort by `position`, then `id` as a tiebreaker, so a corrupted ordering degrades to a
stable arbitrary order rather than a flickering one.

### Move semantics

`POST /api/cards/{id}/move` with `{columnId, position}`:

1. Remove the card from its source column, closing the gap there.
2. Insert it into the target column at `position`, shifting later cards right.
3. Renumber both columns densely.

`position` is clamped to the target column's length, so "move to the end" is any
sufficiently large index. Source and target may be the same column; a within-column move is
the same code path.

## Cascade rules

- Deleting a user deletes their boards, and everything under them.
- Deleting a board deletes its columns and messages.
- Deleting a column deletes its cards.
- Deleting a card deletes nothing else, and closes the position gap in its column.

Cascades are declared in both places: `ondelete="CASCADE"` on the FK, so SQLite enforces it,
and `cascade="all, delete-orphan"` on the relationship, so the ORM session agrees rather
than leaving stale objects behind.

The MVP exposes no delete route for users, boards or columns. The rules are declared anyway
because a schema that only half-describes its own integrity is a trap for later work.

## Seeding

On startup, if the `users` table has no `user` row:

1. Insert `user` with the hash of `password`.
2. Insert one board, titled `Kanban Studio`.
3. Insert the five demo columns: Backlog, Discovery, In Progress, Review, Done
   (positions 0 to 4).
4. Insert the eight demo cards from `frontend/src/lib/kanban.ts`, in their current columns
   and order.

Seeding is keyed on the user's existence, so it runs once and is a no-op on every later
start, including after a container restart with the volume intact.

Step 4 goes slightly beyond the Part 5 outline in `PLAN.md`, which mentions seeding columns
only. Seeding the cards too means a first run looks exactly like the demo the frontend
already ships, and it gives the Part 7 and 9 end-to-end tests real cards to move around
without a fixture step. Say so if you would rather the board start empty.

## API shape

The API speaks the frontend's existing `BoardData` shape. The relational schema is an
implementation detail, assembled on read and diffed on write.

```ts
type Card = { id: string; title: string; details: string };
type Column = { id: string; title: string; cardIds: string[] };
type BoardData = { columns: Column[]; cards: Record<string, Card> };
```

Ids are integer primary keys in the database, serialised as **strings** in JSON (`"3"`, not
`3`). The frontend's types, dnd-kit ids and `data-testid` values are all strings already,
so this keeps `BoardData` unchanged. Ids are opaque to the client: it round-trips whatever
the server sent and never parses or constructs one.

`columns` is ordered by position. `cards` is a flat map keyed by card id; the ordering
lives in each column's `cardIds`.

## Worked example: the seeded board

As rows, immediately after seeding.

`users`

| id | username | password_hash | created_at |
|----|----------|---------------|------------|
| 1  | user     | pbkdf2_sha256$600000$9f2c...$4a71... | 2026-08-13T09:00:00Z |

`boards`

| id | user_id | title         | created_at | updated_at |
|----|---------|---------------|------------|------------|
| 1  | 1       | Kanban Studio | 2026-08-13T09:00:00Z | 2026-08-13T09:00:00Z |

`columns`

| id | board_id | title       | position |
|----|----------|-------------|----------|
| 1  | 1        | Backlog     | 0        |
| 2  | 1        | Discovery   | 1        |
| 3  | 1        | In Progress | 2        |
| 4  | 1        | Review      | 3        |
| 5  | 1        | Done        | 4        |

`cards`

| id | column_id | title                     | details                                                  | position |
|----|-----------|---------------------------|----------------------------------------------------------|----------|
| 1  | 1         | Align roadmap themes      | Draft quarterly themes with impact statements and metrics. | 0 |
| 2  | 1         | Gather customer signals   | Review support tags, sales notes, and churn feedback.      | 1 |
| 3  | 2         | Prototype analytics view  | Sketch initial dashboard layout and key drill-downs.       | 0 |
| 4  | 3         | Refine status language    | Standardize column labels and tone across the board.       | 0 |
| 5  | 3         | Design card layout        | Add hierarchy and spacing for scanning dense lists.        | 1 |
| 6  | 4         | QA micro-interactions     | Verify hover, focus, and loading states.                   | 0 |
| 7  | 5         | Ship marketing page       | Final copy approved and asset pack delivered.              | 0 |
| 8  | 5         | Close onboarding sprint   | Document release notes and share internally.               | 1 |

`messages` is empty.

The same board from `GET /api/board`:

```json
{
  "columns": [
    { "id": "1", "title": "Backlog", "cardIds": ["1", "2"] },
    { "id": "2", "title": "Discovery", "cardIds": ["3"] },
    { "id": "3", "title": "In Progress", "cardIds": ["4", "5"] },
    { "id": "4", "title": "Review", "cardIds": ["6"] },
    { "id": "5", "title": "Done", "cardIds": ["7", "8"] }
  ],
  "cards": {
    "1": {
      "id": "1",
      "title": "Align roadmap themes",
      "details": "Draft quarterly themes with impact statements and metrics."
    },
    "2": {
      "id": "2",
      "title": "Gather customer signals",
      "details": "Review support tags, sales notes, and churn feedback."
    },
    "3": {
      "id": "3",
      "title": "Prototype analytics view",
      "details": "Sketch initial dashboard layout and key drill-downs."
    },
    "4": {
      "id": "4",
      "title": "Refine status language",
      "details": "Standardize column labels and tone across the board."
    },
    "5": {
      "id": "5",
      "title": "Design card layout",
      "details": "Add hierarchy and spacing for scanning dense lists."
    },
    "6": {
      "id": "6",
      "title": "QA micro-interactions",
      "details": "Verify hover, focus, and loading states."
    },
    "7": {
      "id": "7",
      "title": "Ship marketing page",
      "details": "Final copy approved and asset pack delivered."
    },
    "8": {
      "id": "8",
      "title": "Close onboarding sprint",
      "details": "Document release notes and share internally."
    }
  }
}
```

### A move, worked through

Dragging card 6 ("QA micro-interactions") from Review to the top of Done is
`POST /api/cards/6/move` with `{"columnId": "5", "position": 0}`. Afterwards:

| id | column_id | position |
|----|-----------|----------|
| 6  | 5         | 0        |
| 7  | 5         | 1        |
| 8  | 5         | 2        |

Review is now empty, and `GET /api/board` returns `"cardIds": []` for it and
`["6", "7", "8"]` for Done.

## Scope of the API

Every route resolves the board from the session user rather than trusting an id from the
client. A column or card belonging to another user returns 404, not 403 - the MVP does not
confirm the existence of other users' rows.

There is one board per user, so `GET /api/board` takes no id.

## Not covered

No migrations. The schema is created from the models; a schema change during the MVP means
deleting `pm.db` (or the `pm-data` volume) and letting it reseed. Multi-user signup,
multiple boards per user and message pruning are all future work that the schema leaves
room for but does not implement.
