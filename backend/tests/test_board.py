import pytest

from app import db
from app.models import Board, BoardColumn, Card, User
from app.security import hash_password


def read_board(client):
    response = client.get("/api/board")
    assert response.status_code == 200
    return response.json()


def column_by_title(board, title):
    return next(column for column in board["columns"] if column["title"] == title)


def test_seeded_board_is_returned_in_position_order(signed_in):
    board = read_board(signed_in)

    assert [column["title"] for column in board["columns"]] == [
        "Backlog",
        "Discovery",
        "In Progress",
        "Review",
        "Done",
    ]
    backlog = board["columns"][0]
    assert [board["cards"][card_id]["title"] for card_id in backlog["cardIds"]] == [
        "Align roadmap themes",
        "Gather customer signals",
    ]
    assert len(board["cards"]) == 8


def test_column_rename_persists(signed_in):
    column_id = read_board(signed_in)["columns"][0]["id"]

    response = signed_in.patch(f"/api/columns/{column_id}", json={"title": "Ideas"})
    assert response.status_code == 200
    assert response.json()["columns"][0]["title"] == "Ideas"
    assert read_board(signed_in)["columns"][0]["title"] == "Ideas"


def test_card_create_appends_at_the_end(signed_in):
    column = read_board(signed_in)["columns"][0]

    response = signed_in.post(
        f"/api/columns/{column['id']}/cards",
        json={"title": "Third card", "details": "Notes"},
    )
    assert response.status_code == 200
    body = response.json()
    new_id = body["card"]["id"]

    assert body["card"]["title"] == "Third card"
    assert body["board"]["columns"][0]["cardIds"] == [*column["cardIds"], new_id]
    assert read_board(signed_in)["cards"][new_id]["details"] == "Notes"


def test_card_create_defaults_details_to_empty(signed_in):
    column_id = read_board(signed_in)["columns"][0]["id"]

    response = signed_in.post(f"/api/columns/{column_id}/cards", json={"title": "Bare"})
    assert response.json()["card"]["details"] == ""


def test_card_edit_updates_title_and_details_independently(signed_in):
    board = read_board(signed_in)
    card_id = board["columns"][0]["cardIds"][0]
    original = board["cards"][card_id]

    signed_in.patch(f"/api/cards/{card_id}", json={"title": "Retitled"})
    after_title = read_board(signed_in)["cards"][card_id]
    assert after_title == {
        "id": card_id,
        "title": "Retitled",
        "details": original["details"],
    }

    signed_in.patch(f"/api/cards/{card_id}", json={"details": "New details"})
    after_details = read_board(signed_in)["cards"][card_id]
    assert after_details == {
        "id": card_id,
        "title": "Retitled",
        "details": "New details",
    }


def test_card_delete_removes_it_and_closes_the_gap(signed_in):
    backlog = read_board(signed_in)["columns"][0]
    first, second = backlog["cardIds"]

    response = signed_in.delete(f"/api/cards/{first}")
    assert response.status_code == 200

    board = read_board(signed_in)
    assert first not in board["cards"]
    assert board["columns"][0]["cardIds"] == [second]
    with db.SessionLocal() as session:
        assert session.get(Card, int(second)).position == 0


# The card is removed before being inserted, so moving the first card to index 1
# lands it after the other one, and any index past the end means "last".
@pytest.mark.parametrize(
    ("position", "expected_order"),
    [(0, [0, 1]), (1, [1, 0]), (99, [1, 0])],
)
def test_move_within_a_column(signed_in, position, expected_order):
    backlog = read_board(signed_in)["columns"][0]
    original = backlog["cardIds"]

    response = signed_in.post(
        f"/api/cards/{original[0]}/move",
        json={"columnId": backlog["id"], "position": position},
    )
    assert response.status_code == 200
    assert response.json()["columns"][0]["cardIds"] == [
        original[index] for index in expected_order
    ]


def test_move_across_columns_inserts_at_the_requested_index(signed_in):
    board = read_board(signed_in)
    backlog = board["columns"][0]
    in_progress = column_by_title(board, "In Progress")
    moved = backlog["cardIds"][0]

    response = signed_in.post(
        f"/api/cards/{moved}/move",
        json={"columnId": in_progress["id"], "position": 1},
    )
    assert response.status_code == 200

    after = read_board(signed_in)
    assert after["columns"][0]["cardIds"] == backlog["cardIds"][1:]
    assert column_by_title(after, "In Progress")["cardIds"] == [
        in_progress["cardIds"][0],
        moved,
        in_progress["cardIds"][1],
    ]


def test_move_leaves_both_columns_contiguous(signed_in):
    board = read_board(signed_in)
    moved = board["columns"][0]["cardIds"][0]
    done = column_by_title(board, "Done")

    signed_in.post(
        f"/api/cards/{moved}/move", json={"columnId": done["id"], "position": 0}
    )

    with db.SessionLocal() as session:
        for column in session.get(Board, 1).columns:
            positions = [card.position for card in column.cards]
            assert positions == list(range(len(positions)))


def test_move_to_an_empty_column(signed_in):
    board = read_board(signed_in)
    discovery = column_by_title(board, "Discovery")
    only_card = discovery["cardIds"][0]
    done = column_by_title(board, "Done")

    signed_in.post(
        f"/api/cards/{only_card}/move", json={"columnId": done["id"], "position": 0}
    )

    after = read_board(signed_in)
    assert column_by_title(after, "Discovery")["cardIds"] == []
    assert column_by_title(after, "Done")["cardIds"][0] == only_card


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/api/board", None),
        ("patch", "/api/columns/1", {"title": "x"}),
        ("post", "/api/columns/1/cards", {"title": "x"}),
        ("patch", "/api/cards/1", {"title": "x"}),
        ("delete", "/api/cards/1", None),
        ("post", "/api/cards/1/move", {"columnId": "1", "position": 0}),
    ],
)
def test_every_route_requires_a_session(client, method, path, body):
    response = (
        getattr(client, method)(path, json=body)
        if body
        else getattr(client, method)(path)
    )
    assert response.status_code == 401


def test_another_users_rows_are_not_reachable(signed_in):
    with db.SessionLocal() as session:
        other = User(username="other", password_hash=hash_password("x"))
        column = BoardColumn(title="Theirs", position=0)
        column.cards = [Card(title="Theirs", details="", position=0)]
        other.boards = [Board(title="Other board", columns=[column])]
        session.add(other)
        session.commit()
        column_id, card_id = column.id, column.cards[0].id

    assert (
        signed_in.patch(f"/api/columns/{column_id}", json={"title": "x"}).status_code
        == 404
    )
    assert (
        signed_in.post(
            f"/api/columns/{column_id}/cards", json={"title": "x"}
        ).status_code
        == 404
    )
    assert (
        signed_in.patch(f"/api/cards/{card_id}", json={"title": "x"}).status_code == 404
    )
    assert signed_in.delete(f"/api/cards/{card_id}").status_code == 404
    assert card_id not in read_board(signed_in)["cards"]


def test_unknown_ids_are_404(signed_in):
    assert signed_in.patch("/api/columns/999", json={"title": "x"}).status_code == 404
    assert signed_in.delete("/api/cards/999").status_code == 404
    card_id = read_board(signed_in)["columns"][0]["cardIds"][0]
    response = signed_in.post(
        f"/api/cards/{card_id}/move", json={"columnId": "999", "position": 0}
    )
    assert response.status_code == 404


def test_malformed_ids_are_4xx_not_500(signed_in):
    assert signed_in.delete("/api/cards/abc").status_code == 422
    card_id = read_board(signed_in)["columns"][0]["cardIds"][0]
    response = signed_in.post(
        f"/api/cards/{card_id}/move", json={"columnId": "abc", "position": 0}
    )
    assert response.status_code == 404


def test_invalid_bodies_are_rejected(signed_in):
    board = read_board(signed_in)
    column_id = board["columns"][0]["id"]
    card_id = board["columns"][0]["cardIds"][0]

    assert (
        signed_in.patch(f"/api/columns/{column_id}", json={"title": "  "}).status_code
        == 422
    )
    assert (
        signed_in.post(
            f"/api/columns/{column_id}/cards", json={"title": ""}
        ).status_code
        == 422
    )
    assert (
        signed_in.patch(f"/api/cards/{card_id}", json={"title": " "}).status_code == 422
    )
    response = signed_in.post(
        f"/api/cards/{card_id}/move", json={"columnId": column_id, "position": -1}
    )
    assert response.status_code == 422


def test_titles_are_trimmed(signed_in):
    column_id = read_board(signed_in)["columns"][0]["id"]
    response = signed_in.post(
        f"/api/columns/{column_id}/cards", json={"title": "  Spaced  "}
    )
    assert response.json()["card"]["title"] == "Spaced"
