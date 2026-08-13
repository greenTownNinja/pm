from typing import Annotated, Literal

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


class ChatRequest(BaseModel):
    message: Title


class MessageOut(BaseModel):
    role: str
    content: str


class ChatOut(BaseModel):
    reply: str
    board: BoardOut


class Action(BaseModel):
    """One board change asked for by the model. Fields it does not need are null."""

    action: Literal[
        "create_card", "edit_card", "move_card", "delete_card", "rename_column"
    ]
    cardId: str | None = None
    columnId: str | None = None
    title: str | None = None
    details: str | None = None
    position: int | None = None


class ModelReply(BaseModel):
    """The model's structured response, validated before anything is applied."""

    reply: str
    updates: list[Action] | None = None
