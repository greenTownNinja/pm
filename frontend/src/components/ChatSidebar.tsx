"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import * as api from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatSidebarProps = {
  isOpen: boolean;
  onToggle: () => void;
  /** The board as the AI left it, applied without a second request. */
  onBoardUpdate: (board: BoardData) => void;
};

export const ChatSidebar = ({ isOpen, onToggle, onBoardUpdate }: ChatSidebarProps) => {
  const [messages, setMessages] = useState<api.ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.fetchChatHistory().then(setMessages, () => {});
  }, []);

  // Follow the conversation as it grows, including the pending indicator.
  useEffect(() => {
    const feed = feedRef.current;
    if (feed) {
      feed.scrollTop = feed.scrollHeight;
    }
  }, [messages, isSending]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isSending) {
      return;
    }

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setDraft("");
    setError(null);
    setIsSending(true);

    try {
      const { reply, board } = await api.sendChatMessage(message);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      onBoardUpdate(board);
    } catch (cause) {
      // The turn never happened on the server, so take the message back off the
      // feed and return it to the input for another go.
      setMessages((prev) => prev.slice(0, -1));
      setDraft(message);
      setError(cause instanceof Error ? cause.message : "Could not send that message.");
    } finally {
      setIsSending(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-[var(--secondary-purple)] px-6 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white shadow-[var(--shadow)] transition hover:brightness-110"
      >
        Ask AI
      </button>
    );
  }

  return (
    <aside
      data-testid="chat-sidebar"
      aria-label="AI assistant"
      className="fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-[var(--stroke)] bg-white shadow-[var(--shadow)] sm:w-[400px]"
    >
      <header className="flex items-start justify-between gap-4 border-b border-[var(--stroke)] px-6 py-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Assistant
          </p>
          <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
            Ask about your board
          </h2>
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Close assistant"
          className="rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
        >
          Close
        </button>
      </header>

      <div ref={feedRef} className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        {messages.length === 0 && !isSending ? (
          <p className="text-sm leading-6 text-[var(--gray-text)]">
            Ask what is on the board, or tell the assistant to add, edit, move or
            delete cards.
          </p>
        ) : null}

        {messages.map((message, index) => (
          <article
            key={index}
            data-testid={`message-${message.role}`}
            className={
              message.role === "user"
                ? "ml-8 rounded-2xl bg-[var(--surface-strong)] px-4 py-3"
                : "mr-8 rounded-2xl border border-[var(--stroke)] px-4 py-3"
            }
          >
            <p className="text-[10px] font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              {message.role === "user" ? "You" : "Assistant"}
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[var(--navy-dark)]">
              {message.content}
            </p>
          </article>
        ))}

        {isSending ? (
          <p className="text-xs uppercase tracking-[0.3em] text-[var(--primary-blue)]">
            Thinking
          </p>
        ) : null}
      </div>

      <form
        onSubmit={handleSubmit}
        className="space-y-3 border-t border-[var(--stroke)] px-6 py-5"
      >
        {error ? (
          <p role="alert" className="text-sm text-[var(--secondary-purple)]">
            {error}
          </p>
        ) : null}
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          aria-label="Message"
          placeholder="Move the QA card to Done"
          rows={3}
          className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={isSending}
          className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:opacity-60"
        >
          {isSending ? "Sending" : "Send"}
        </button>
      </form>
    </aside>
  );
};
