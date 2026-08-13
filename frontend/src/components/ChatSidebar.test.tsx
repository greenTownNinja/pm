import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatSidebar } from "@/components/ChatSidebar";
import { boardFixture } from "@/test/board-fixture";
import type { BoardData } from "@/lib/kanban";

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body });
const failed = () => ({
  ok: false,
  status: 502,
  json: async () => ({ detail: "The assistant is offline" }),
});

/** Routes /api/chat/history to `history` and answers POST /api/chat with `reply`. */
const mockApi = (options: { history?: unknown; reply?: unknown } = {}) => {
  const { history = [], reply = ok({ reply: "Done.", board: boardFixture }) } = options;
  const fetchMock = vi.fn(async (path: string) =>
    path === "/api/chat/history" ? ok(history) : reply
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

const renderSidebar = (onBoardUpdate: (board: BoardData) => void = () => {}) =>
  render(
    <ChatSidebar isOpen onToggle={() => {}} onBoardUpdate={onBoardUpdate} />
  );

const send = async (message: string) => {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Message"), message);
  await user.click(screen.getByRole("button", { name: "Send" }));
};

describe("ChatSidebar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the stored conversation on mount", async () => {
    mockApi({
      history: [
        { role: "user", content: "what is on my board?" },
        { role: "assistant", content: "Five columns." },
      ],
    });
    renderSidebar();

    expect(await screen.findByText("what is on my board?")).toBeInTheDocument();
    expect(screen.getByText("Five columns.")).toBeInTheDocument();
  });

  it("shows the user message, then the reply", async () => {
    mockApi({ reply: ok({ reply: "Card added.", board: boardFixture }) });
    renderSidebar();

    await send("add a card to Backlog");

    expect(await screen.findByText("Card added.")).toBeInTheDocument();
    expect(screen.getByText("add a card to Backlog")).toBeInTheDocument();
    expect(screen.getByTestId("message-user")).toBeInTheDocument();
  });

  it("sends the message to the chat endpoint", async () => {
    const fetchMock = mockApi();
    renderSidebar();

    await send("hello");

    await waitFor(() => {
      const [path, init] = fetchMock.mock.calls.at(-1) as unknown as [
        string,
        RequestInit,
      ];
      expect(path).toBe("/api/chat");
      expect(init.method).toBe("POST");
      expect(JSON.parse(String(init.body))).toEqual({ message: "hello" });
    });
  });

  it("hands the updated board back so the Kanban re-renders", async () => {
    const updated: BoardData = {
      ...boardFixture,
      columns: boardFixture.columns.map((column, index) =>
        index === 0 ? { ...column, title: "Icebox" } : column
      ),
    };
    mockApi({ reply: ok({ reply: "Renamed.", board: updated }) });
    const onBoardUpdate = vi.fn();
    renderSidebar(onBoardUpdate);

    await send("rename Backlog to Icebox");

    await waitFor(() => expect(onBoardUpdate).toHaveBeenCalledWith(updated));
  });

  it("keeps the message for a retry when the request fails", async () => {
    mockApi({ reply: failed() });
    renderSidebar();

    await send("move the QA card");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The assistant is offline"
    );
    expect(screen.getByLabelText("Message")).toHaveValue("move the QA card");
    expect(screen.queryByTestId("message-user")).not.toBeInTheDocument();
  });

  it("shows a pending indicator while the model answers", async () => {
    const fetchMock = vi.fn(async (path: string) =>
      path === "/api/chat/history"
        ? ok([])
        : new Promise((resolve) =>
            setTimeout(() => resolve(ok({ reply: "Late.", board: boardFixture })), 20)
          )
    );
    vi.stubGlobal("fetch", fetchMock);
    renderSidebar();

    await send("hello");

    expect(screen.getByText("Thinking")).toBeInTheDocument();
    expect(await screen.findByText("Late.")).toBeInTheDocument();
    expect(screen.queryByText("Thinking")).not.toBeInTheDocument();
  });

  it("renders a toggle instead of the panel when closed", async () => {
    const fetchMock = mockApi();
    render(<ChatSidebar isOpen={false} onToggle={() => {}} onBoardUpdate={() => {}} />);

    expect(screen.getByRole("button", { name: "Ask AI" })).toBeInTheDocument();
    expect(screen.queryByTestId("chat-sidebar")).not.toBeInTheDocument();
    // Let the history load settle so it does not update state after the test.
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  });
});
