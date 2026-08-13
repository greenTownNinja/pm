"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import * as api from "@/lib/api";
import { emptyBoard, moveCard, resolveDrop, type BoardData } from "@/lib/kanban";

const RENAME_DEBOUNCE_MS = 400;

type KanbanBoardProps = {
  username: string;
  onSignOut: () => void;
};

export const KanbanBoard = ({ username, onSignOut }: KanbanBoardProps) => {
  const [board, setBoard] = useState<BoardData>(emptyBoard);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  // The last board the server confirmed, and what a failed mutation rolls back to.
  const confirmed = useRef<BoardData>(emptyBoard);
  const pendingRenames = useRef(
    new Map<string, { timer: ReturnType<typeof setTimeout>; title: string }>()
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // State is set from the promise callbacks, never synchronously, so mounting this
  // does not cascade renders.
  const load = useCallback(() => {
    api.fetchBoard().then(
      (data) => {
        confirmed.current = data;
        setBoard(data);
        setStatus("ready");
      },
      () => setStatus("error")
    );
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Send anything still waiting on the debounce rather than dropping it on unmount.
  useEffect(() => {
    const pending = pendingRenames.current;
    return () =>
      pending.forEach(({ timer, title }, columnId) => {
        clearTimeout(timer);
        api.renameColumn(columnId, title).catch(() => {});
      });
  }, []);

  /** Runs a mutation whose optimistic result is already on screen. */
  const save = async (call: () => Promise<BoardData>) => {
    try {
      confirmed.current = await call();
      setSaveError(null);
    } catch (cause) {
      setBoard(confirmed.current);
      setSaveError(cause instanceof Error ? cause.message : "Could not save that change.");
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    const activeId = active.id as string;
    const drop = resolveDrop(board.columns, activeId, over.id as string);
    if (!drop) {
      return;
    }

    setBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, activeId, over.id as string),
    }));
    save(() => api.moveCard(activeId, drop.columnId, drop.position));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));

    // Debounced: the input renames on every keystroke.
    clearTimeout(pendingRenames.current.get(columnId)?.timer);
    pendingRenames.current.set(columnId, {
      title,
      timer: setTimeout(() => {
        pendingRenames.current.delete(columnId);
        save(() => api.renameColumn(columnId, title));
      }, RENAME_DEBOUNCE_MS),
    });
  };

  // Not optimistic: only the server can assign the new card's id.
  const handleAddCard = async (columnId: string, title: string, details: string) => {
    try {
      const { board: next } = await api.createCard(columnId, title, details);
      confirmed.current = next;
      setBoard(next);
      setSaveError(null);
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : "Could not add that card.");
    }
  };

  const handleEditCard = (cardId: string, title: string, details: string) => {
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [cardId]: { ...prev.cards[cardId], title, details },
      },
    }));
    save(() => api.updateCard(cardId, { title, details }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    setBoard((prev) => ({
      ...prev,
      cards: Object.fromEntries(
        Object.entries(prev.cards).filter(([id]) => id !== cardId)
      ),
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: column.cardIds.filter((id) => id !== cardId) }
          : column
      ),
    }));
    save(() => api.deleteCard(cardId));
  };

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm uppercase tracking-[0.3em] text-[var(--gray-text)]">
          Loading board
        </p>
      </main>
    );
  }

  if (status === "error") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p role="alert" className="text-sm text-[var(--navy-dark)]">
          Could not load your board.
        </p>
        <button
          type="button"
          onClick={() => {
            setStatus("loading");
            load();
          }}
          className="rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
        >
          Try again
        </button>
      </main>
    );
  }

  const activeCard = activeCardId ? board.cards[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex flex-col items-end gap-3">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  {username}
                </span>
                <button
                  type="button"
                  onClick={onSignOut}
                  className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--secondary-purple)] transition hover:border-[var(--secondary-purple)]"
                >
                  Sign out
                </button>
              </div>
            </div>
          </div>
          {saveError ? (
            <p
              role="alert"
              className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--secondary-purple)]"
            >
              {saveError}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onEditCard={handleEditCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
