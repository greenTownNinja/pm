from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.db import get_db
from app.models import Board, BoardColumn, Card, User, utcnow
from app.schemas import (
    BoardOut,
    CardCreate,
    CardCreatedOut,
    CardMove,
    CardOut,
    CardUpdate,
    ColumnOut,
    ColumnRename,
)

router = APIRouter(prefix="/api")

Db = Annotated[Session, Depends(get_db)]


def serialize(board: Board) -> BoardOut:
    return BoardOut(
        columns=[
            ColumnOut(
                id=str(column.id),
                title=column.title,
                cardIds=[str(card.id) for card in column.cards],
            )
            for column in board.columns
        ],
        cards={
            str(card.id): CardOut(
                id=str(card.id), title=card.title, details=card.details
            )
            for column in board.columns
            for card in column.cards
        },
    )


def renumber(cards: list[Card]) -> None:
    for position, card in enumerate(cards):
        card.position = position


def place_card(card: Card, target: BoardColumn, position: int) -> None:
    """Remove the card from its column, then insert it into the target at position."""
    source = card.column
    source_cards = [other for other in source.cards if other.id != card.id]
    target_cards = source_cards if target.id == source.id else list(target.cards)
    # Past the end means "last", so a move to the bottom needs no exact index.
    target_cards.insert(min(position, len(target_cards)), card)

    card.column = target
    renumber(source_cards)
    renumber(target_cards)


def parse_id(value: str) -> int:
    """Ids are opaque strings to the client, so a non-numeric one is just a miss."""
    if not value.isdigit():
        raise HTTPException(status_code=404, detail="Not found")
    return int(value)


def load_board(db: Db, user: CurrentUser) -> Board:
    board = db.scalar(
        select(Board).join(Board.user).where(User.username == user.username)
    )
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


def load_column(db: Db, user: CurrentUser, column_id: int) -> BoardColumn:
    column = db.get(BoardColumn, column_id)
    # Another user's column is a 404, not a 403: their rows are none of our business.
    if column is None or column.board.user.username != user.username:
        raise HTTPException(status_code=404, detail="Column not found")
    return column


def load_card(db: Db, user: CurrentUser, card_id: int) -> Card:
    card = db.get(Card, card_id)
    if card is None or card.column.board.user.username != user.username:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.get("/board")
def read_board(db: Db, user: CurrentUser) -> BoardOut:
    return serialize(load_board(db, user))


@router.patch("/columns/{column_id}")
def rename_column(
    column_id: int, body: ColumnRename, db: Db, user: CurrentUser
) -> BoardOut:
    column = load_column(db, user, column_id)
    column.title = body.title
    column.board.updated_at = utcnow()
    db.commit()
    return serialize(column.board)


@router.post("/columns/{column_id}/cards")
def create_card(
    column_id: int, body: CardCreate, db: Db, user: CurrentUser
) -> CardCreatedOut:
    column = load_column(db, user, column_id)
    card = Card(
        title=body.title,
        details=body.details,
        position=len(column.cards),
        column=column,
    )
    column.board.updated_at = utcnow()
    db.add(card)
    db.commit()
    return CardCreatedOut(
        card=CardOut(id=str(card.id), title=card.title, details=card.details),
        board=serialize(column.board),
    )


@router.patch("/cards/{card_id}")
def update_card(card_id: int, body: CardUpdate, db: Db, user: CurrentUser) -> BoardOut:
    card = load_card(db, user, card_id)
    if body.title is not None:
        card.title = body.title
    if body.details is not None:
        card.details = body.details
    board = card.column.board
    board.updated_at = utcnow()
    db.commit()
    return serialize(board)


@router.delete("/cards/{card_id}")
def delete_card(card_id: int, db: Db, user: CurrentUser) -> BoardOut:
    card = load_card(db, user, card_id)
    column = card.column
    board = column.board
    remaining = [other for other in column.cards if other.id != card.id]

    db.delete(card)
    renumber(remaining)
    board.updated_at = utcnow()
    db.commit()
    return serialize(board)


@router.post("/cards/{card_id}/move")
def move_card(card_id: int, body: CardMove, db: Db, user: CurrentUser) -> BoardOut:
    card = load_card(db, user, card_id)
    target = load_column(db, user, parse_id(body.columnId))
    board = target.board

    place_card(card, target, body.position)
    board.updated_at = utcnow()
    db.commit()
    return serialize(board)
