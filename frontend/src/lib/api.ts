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
