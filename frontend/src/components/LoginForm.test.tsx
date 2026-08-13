import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginForm } from "@/components/LoginForm";

const submitCredentials = async (username: string, password: string) => {
  await userEvent.type(screen.getByLabelText("Username"), username);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
};

describe("LoginForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits credentials and reports the signed-in user", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ username: "user" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onSignedIn = vi.fn();

    render(<LoginForm onSignedIn={onSignedIn} />);
    await submitCredentials("user", "password");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ username: "user", password: "password" }),
      })
    );
    expect(onSignedIn).toHaveBeenCalledWith({ username: "user" });
  });

  it("surfaces the error from a failed sign in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Invalid username or password" }),
      })
    );
    const onSignedIn = vi.fn();

    render(<LoginForm onSignedIn={onSignedIn} />);
    await submitCredentials("user", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid username or password"
    );
    expect(onSignedIn).not.toHaveBeenCalled();
  });
});
