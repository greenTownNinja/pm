import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { boardFixture } from "@/test/board-fixture";
import type { BoardData } from "@/lib/kanban";

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
const failed = () => ({
  ok: false,
  status: 500,
  json: async () => ({ detail: "Server exploded" }),
});

/** Routes /api/board to the fixture and answers every mutation with `mutationBody`. */
const mockApi = (mutationBody: unknown = boardFixture) => {
  const fetchMock = vi.fn(async (path: string, init?: RequestInit) =>
    path === "/api/board" && !init?.method ? ok(boardFixture) : ok(mutationBody)
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

const renderBoard = async () => {
  render(<KanbanBoard username="user" onSignOut={() => {}} />);
  await screen.findByRole("heading", { name: "Kanban Studio" });
};

const firstColumn = () => screen.getAllByTestId(/column-/i)[0];

const lastCall = (fetchMock: ReturnType<typeof vi.fn>) =>
  fetchMock.mock.calls.at(-1) as [string, RequestInit];

describe("KanbanBoard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the board returned by the API", async () => {
    mockApi();
    await renderBoard();

    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    expect(screen.getByText("Align roadmap themes")).toBeInTheDocument();
  });

  it("shows a loading state until the board arrives", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        () => new Promise((resolve) => setTimeout(() => resolve(ok(boardFixture)), 20))
      )
    );
    render(<KanbanBoard username="user" onSignOut={() => {}} />);

    expect(screen.getByText(/loading board/i)).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
  });

  it("shows an error state and retries", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(failed())
      .mockResolvedValue(ok(boardFixture));
    vi.stubGlobal("fetch", fetchMock);
    render(<KanbanBoard username="user" onSignOut={() => {}} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /could not load your board/i
    );

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(
      await screen.findByRole("heading", { name: "Kanban Studio" })
    ).toBeInTheDocument();
  });

  it("debounces a column rename into one request", async () => {
    const fetchMock = mockApi();
    await renderBoard();

    const input = within(firstColumn()).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Ideas");
    expect(input).toHaveValue("Ideas");

    await waitFor(() => {
      const [path, init] = lastCall(fetchMock);
      expect(path).toBe("/api/columns/col-backlog");
      expect(init.method).toBe("PATCH");
      expect(init.body).toBe(JSON.stringify({ title: "Ideas" }));
    });
    const renames = fetchMock.mock.calls.filter(([path]) =>
      String(path).startsWith("/api/columns/")
    );
    expect(renames).toHaveLength(1);
  });

  it("creates a card and renders the board the server returns", async () => {
    const created: BoardData = {
      columns: boardFixture.columns.map((column) =>
        column.id === "col-backlog"
          ? { ...column, cardIds: [...column.cardIds, "card-99"] }
          : column
      ),
      cards: {
        ...boardFixture.cards,
        "card-99": { id: "card-99", title: "New card", details: "Notes" },
      },
    };
    const fetchMock = mockApi({ card: created.cards["card-99"], board: created });
    await renderBoard();

    const column = firstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.type(
      within(column).getByPlaceholderText(/card title/i),
      "New card"
    );
    await userEvent.type(within(column).getByPlaceholderText(/details/i), "Notes");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    const [path, init] = lastCall(fetchMock);
    expect(path).toBe("/api/columns/col-backlog/cards");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ title: "New card", details: "Notes" }));
    expect(await within(column).findByText("New card")).toBeInTheDocument();
  });

  it("edits a card", async () => {
    const fetchMock = mockApi();
    await renderBoard();

    const column = firstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /edit align roadmap themes/i })
    );
    const titleInput = within(column).getByLabelText("Edit title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Renamed card");
    await userEvent.click(within(column).getByRole("button", { name: /save card/i }));

    expect(within(column).getByText("Renamed card")).toBeInTheDocument();
    const [path, init] = lastCall(fetchMock);
    expect(path).toBe("/api/cards/card-1");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(String(init.body)).title).toBe("Renamed card");
  });

  it("deletes a card", async () => {
    const fetchMock = mockApi();
    await renderBoard();

    const column = firstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /delete align roadmap themes/i })
    );

    expect(within(column).queryByText("Align roadmap themes")).not.toBeInTheDocument();
    const [path, init] = lastCall(fetchMock);
    expect(path).toBe("/api/cards/card-1");
    expect(init.method).toBe("DELETE");
  });

  it("rolls the board back when a mutation fails", async () => {
    const fetchMock = vi.fn(async (path: string, init?: RequestInit) =>
      path === "/api/board" && !init?.method ? ok(boardFixture) : failed()
    );
    vi.stubGlobal("fetch", fetchMock);
    await renderBoard();

    const column = firstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /delete align roadmap themes/i })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Server exploded");
    expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument();
  });
});
