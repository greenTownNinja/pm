import json

import httpx
import pytest

from app import ai, chat
from app.config import settings


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")


@pytest.fixture
def model(monkeypatch):
    """Queue model responses; returns the recorded OpenRouter request payloads."""
    calls = []
    queued = []

    async def post(_self, _url, **kwargs):
        calls.append(kwargs["json"])
        content = queued.pop(0)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": content}}]},
            request=httpx.Request("POST", ai.OPENROUTER_URL),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    def queue(reply="Done.", updates=None, raw=None):
        if raw is None:
            raw = json.dumps({"reply": reply, "updates": updates})
        queued.append(raw)

    queue.calls = calls
    return queue


def action(name, **fields):
    return {"action": name, **fields}


def board_of(client):
    return client.get("/api/board").json()


def test_question_leaves_the_board_untouched(signed_in, model):
    before = board_of(signed_in)
    model(reply="You have five columns.", updates=None)

    response = signed_in.post("/api/chat", json={"message": "what is on my board?"})

    assert response.status_code == 200
    assert response.json()["reply"] == "You have five columns."
    assert response.json()["board"] == before
    assert board_of(signed_in) == before


def test_request_carries_the_board_schema_and_history(signed_in, model):
    model(reply="ok")
    signed_in.post("/api/chat", json={"message": "hello"})
    model(reply="ok again")
    signed_in.post("/api/chat", json={"message": "again"})

    first, second = model.calls
    assert first["response_format"]["json_schema"]["strict"] is True
    assert first["provider"] == {"require_parameters": True}
    assert first["messages"][0]["role"] == "system"
    assert "Backlog" in first["messages"][0]["content"]
    assert first["messages"][1:] == [{"role": "user", "content": "hello"}]
    # The second turn replays the first, in order, before the new message.
    assert second["messages"][1:] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "again"},
    ]


def test_create_card(signed_in, model):
    model(
        updates=[action("create_card", columnId="1", title="Write docs", details="d")]
    )

    board = signed_in.post("/api/chat", json={"message": "add a card"}).json()["board"]

    backlog = board["columns"][0]
    created = board["cards"][backlog["cardIds"][-1]]
    assert created["title"] == "Write docs"
    assert created["details"] == "d"
    assert board_of(signed_in) == board


def test_edit_card(signed_in, model):
    model(updates=[action("edit_card", cardId="1", title="Renamed")])

    board = signed_in.post("/api/chat", json={"message": "rename it"}).json()["board"]

    assert board["cards"]["1"]["title"] == "Renamed"
    # Details are untouched when the action leaves them null.
    assert board["cards"]["1"]["details"].startswith("Draft quarterly")


def test_move_card(signed_in, model):
    model(updates=[action("move_card", cardId="6", columnId="5", position=0)])

    board = signed_in.post("/api/chat", json={"message": "move it"}).json()["board"]

    assert board["columns"][3]["cardIds"] == []
    assert board["columns"][4]["cardIds"] == ["6", "7", "8"]


def test_move_card_without_a_position_goes_to_the_bottom(signed_in, model):
    model(updates=[action("move_card", cardId="6", columnId="5")])

    board = signed_in.post("/api/chat", json={"message": "move it"}).json()["board"]

    assert board["columns"][4]["cardIds"] == ["7", "8", "6"]


def test_delete_card(signed_in, model):
    model(updates=[action("delete_card", cardId="1")])

    board = signed_in.post("/api/chat", json={"message": "delete it"}).json()["board"]

    assert "1" not in board["cards"]
    assert board["columns"][0]["cardIds"] == ["2"]


def test_rename_column(signed_in, model):
    model(updates=[action("rename_column", columnId="1", title="Icebox")])

    board = signed_in.post("/api/chat", json={"message": "rename it"}).json()["board"]

    assert board["columns"][0]["title"] == "Icebox"


def test_multiple_actions_apply_in_order(signed_in, model):
    model(
        updates=[
            action("create_card", columnId="5", title="Fresh"),
            action("rename_column", columnId="5", title="Shipped"),
            action("delete_card", cardId="7"),
        ]
    )

    board = signed_in.post("/api/chat", json={"message": "do it all"}).json()["board"]

    done = board["columns"][4]
    assert done["title"] == "Shipped"
    assert [board["cards"][card_id]["title"] for card_id in done["cardIds"]] == [
        "Close onboarding sprint",
        "Fresh",
    ]


def test_unknown_id_rolls_back_the_whole_batch(signed_in, model):
    before = board_of(signed_in)
    model(
        updates=[
            action("rename_column", columnId="1", title="Icebox"),
            action("delete_card", cardId="9999"),
        ]
    )

    response = signed_in.post("/api/chat", json={"message": "do it"})

    assert response.status_code == 400
    assert "9999" in response.json()["detail"]
    assert board_of(signed_in) == before
    # The failed turn is not recorded either.
    assert signed_in.get("/api/chat/history").json() == []


def test_another_users_card_is_rejected(signed_in, model, client):
    # Card ids are global, so an id that exists but belongs elsewhere must not apply.
    model(updates=[action("edit_card", cardId="abc", title="x")])

    response = signed_in.post("/api/chat", json={"message": "do it"})

    assert response.status_code == 400


def test_empty_title_is_rejected(signed_in, model):
    before = board_of(signed_in)
    model(updates=[action("create_card", columnId="1", title="   ")])

    response = signed_in.post("/api/chat", json={"message": "add one"})

    assert response.status_code == 400
    assert board_of(signed_in) == before


def test_malformed_model_json_is_a_502(signed_in, model):
    model(raw="sorry, no JSON today")

    response = signed_in.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 502


def test_response_missing_reply_is_a_502(signed_in, model):
    model(raw=json.dumps({"updates": None}))

    assert signed_in.post("/api/chat", json={"message": "hello"}).status_code == 502


def test_history_is_persisted_in_order(signed_in, model):
    model(reply="first")
    signed_in.post("/api/chat", json={"message": "one"})
    model(reply="second")
    signed_in.post("/api/chat", json={"message": "two"})

    assert signed_in.get("/api/chat/history").json() == [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "first"},
        {"role": "user", "content": "two"},
        {"role": "assistant", "content": "second"},
    ]


def test_history_sent_to_the_model_is_capped(signed_in, model, monkeypatch):
    monkeypatch.setattr(chat, "HISTORY_LIMIT", 4)
    for turn in range(3):
        model(reply=f"reply {turn}")
        signed_in.post("/api/chat", json={"message": f"message {turn}"})
    model(reply="latest")
    signed_in.post("/api/chat", json={"message": "newest"})

    replayed = model.calls[-1]["messages"][1:]

    assert len(replayed) == 5  # the capped history plus the new message
    assert replayed[0] == {"role": "user", "content": "message 1"}
    assert replayed[-1] == {"role": "user", "content": "newest"}
    # Nothing is lost from the stored history.
    assert len(signed_in.get("/api/chat/history").json()) == 8


def test_chat_requires_authentication(client):
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 401
    assert client.get("/api/chat/history").status_code == 401
