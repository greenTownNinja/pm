import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AppShell } from "@/components/AppShell";

const respond = (ok: boolean, body: unknown) => ({ ok, status: ok ? 200 : 401, json: async () => body });

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
      vi.fn().mockResolvedValue(respond(true, { username: "user" }))
    );

    render(<AppShell />);

    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
  });

  it("returns to the login form after signing out", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(respond(true, { username: "user" }))
      .mockResolvedValueOnce(respond(true, { status: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    render(<AppShell />);
    await userEvent.click(
      await screen.findByRole("button", { name: /sign out/i })
    );

    expect(await screen.findByTestId("login-form")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/logout",
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
  });
});
