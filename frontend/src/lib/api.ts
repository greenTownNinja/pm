import type { BoardData, Card } from "@/lib/kanban";

export type User = { username: string };

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`/api${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
};

export const login = (username: string, password: string) =>
  request<User>("/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

export const logout = () => request<{ status: string }>("/logout", { method: "POST" });

/** The signed-in user, or null when there is no valid session. */
export const me = async (): Promise<User | null> => {
  const response = await fetch("/api/me", { credentials: "include" });
  return response.ok ? ((await response.json()) as User) : null;
};

// Every board mutation answers with the whole board, so the client can reconcile in one
// step. Creating a card also returns the card, since only the server knows its id.

export const fetchBoard = () => request<BoardData>("/board");

export const renameColumn = (columnId: string, title: string) =>
  request<BoardData>(`/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

export const createCard = (columnId: string, title: string, details: string) =>
  request<{ card: Card; board: BoardData }>(`/columns/${columnId}/cards`, {
    method: "POST",
    body: JSON.stringify({ title, details }),
  });

export const updateCard = (
  cardId: string,
  changes: { title?: string; details?: string }
) =>
  request<BoardData>(`/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });

export const deleteCard = (cardId: string) =>
  request<BoardData>(`/cards/${cardId}`, { method: "DELETE" });

export const moveCard = (cardId: string, columnId: string, position: number) =>
  request<BoardData>(`/cards/${cardId}/move`, {
    method: "POST",
    body: JSON.stringify({ columnId, position }),
  });

export type ChatMessage = { role: "user" | "assistant"; content: string };

export const fetchChatHistory = () => request<ChatMessage[]>("/chat/history");

// The reply comes with the board as the AI left it, so a chat turn needs no refetch.
export const sendChatMessage = (message: string) =>
  request<{ reply: string; board: BoardData }>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
