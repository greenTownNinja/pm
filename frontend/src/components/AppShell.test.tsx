import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";
import { boardFixture } from "@/test/board-fixture";

const respond = (ok: boolean, body: unknown) => ({
  ok,
  status: ok ? 200 : 401,
  json: async () => body,
});

/** The board fetch that KanbanBoard fires on mount answers from the fixture. */
const withBoard = (handler: (path: string) => unknown) =>
  vi.fn(async (path: string) =>
    path === "/api/board" ? respond(true, boardFixture) : handler(path)
  );

describe("AppShell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the login form when there is no session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(false, null)));

    render(<AppShell />);

    expect(await screen.findByTestId("login-form")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Kanban Studio" })).not.toBeInTheDocument();
  });

  it("shows the board when the session is valid", async () => {
    vi.stubGlobal(
      "fetch",
      withBoard(() => respond(true, { username: "user" }))
    );

    render(<AppShell />);

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
  });

  it("returns to the login form after signing out", async () => {
    const calls: string[] = [];
    const fetchMock = withBoard((path) => {
      calls.push(path);
      return respond(true, path === "/api/me" ? { username: "user" } : { status: "ok" });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AppShell />);
    await userEvent.click(
      await screen.findByRole("button", { name: /sign out/i })
    );

    expect(await screen.findByTestId("login-form")).toBeInTheDocument();
    expect(calls).toContain("/api/logout");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/logout",
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
  });
});
