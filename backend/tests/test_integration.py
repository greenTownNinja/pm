from tests.conftest import CREDENTIALS


def test_a_full_session_of_changes_is_reflected_in_the_board(client):
    """The sequence the frontend performs: sign in, mutate, read back."""
    assert client.get("/api/board").status_code == 401
    client.post("/api/login", json=CREDENTIALS)

    board = client.get("/api/board").json()
    backlog, review = board["columns"][0], board["columns"][3]

    client.patch(f"/api/columns/{backlog['id']}", json={"title": "Ideas"})
    created = client.post(
        f"/api/columns/{backlog['id']}/cards",
        json={"title": "Wire the UI", "details": "Part 7"},
    ).json()["card"]
    client.patch(f"/api/cards/{created['id']}", json={"details": "Done in Part 7"})
    client.post(
        f"/api/cards/{created['id']}/move",
        json={"columnId": review["id"], "position": 0},
    )
    client.delete(f"/api/cards/{backlog['cardIds'][0]}")

    after = client.get("/api/board").json()
    assert after["columns"][0]["title"] == "Ideas"
    assert after["columns"][0]["cardIds"] == backlog["cardIds"][1:]
    assert after["columns"][3]["cardIds"][0] == created["id"]
    assert after["cards"][created["id"]] == {
        "id": created["id"],
        "title": "Wire the UI",
        "details": "Done in Part 7",
    }
