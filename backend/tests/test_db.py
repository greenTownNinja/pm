from sqlalchemy import select

from app import db
from app.models import Board, BoardColumn, Card, User


def test_database_file_is_created_when_absent(client, tmp_path):
    assert (tmp_path / "pm.db").exists()


def test_seeding_is_idempotent_across_restarts(client):
    db.init_db()
    db.init_db()

    with db.SessionLocal() as session:
        assert len(session.scalars(select(User)).all()) == 1
        assert len(session.scalars(select(Board)).all()) == 1
        assert len(session.scalars(select(BoardColumn)).all()) == 5
        assert len(session.scalars(select(Card)).all()) == 8


def test_password_is_stored_hashed(client):
    with db.SessionLocal() as session:
        user = session.scalar(select(User))
        assert user.password_hash.startswith("pbkdf2_sha256$")
        assert "password" not in user.password_hash


def test_deleting_a_board_cascades_to_columns_and_cards(client):
    with db.SessionLocal() as session:
        session.delete(session.scalar(select(Board)))
        session.commit()

        assert session.scalars(select(BoardColumn)).all() == []
        assert session.scalars(select(Card)).all() == []
