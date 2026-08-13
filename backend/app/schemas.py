from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# Titles are trimmed and may not be blank.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CardOut(BaseModel):
    id: str
    title: str
    details: str


class ColumnOut(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardOut(BaseModel):
    """The frontend's BoardData shape: ordered columns plus a flat card map."""

    columns: list[ColumnOut]
    cards: dict[str, CardOut]


class CardCreatedOut(BaseModel):
    card: CardOut
    board: BoardOut


class ColumnRename(BaseModel):
    title: Title


class CardCreate(BaseModel):
    title: Title
    details: str = ""


class CardUpdate(BaseModel):
    title: Title | None = None
    details: str | None = None


class CardMove(BaseModel):
    columnId: str
    position: int = Field(ge=0)
