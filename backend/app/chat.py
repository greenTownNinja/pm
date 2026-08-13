import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app import ai
from app.auth import CurrentUser
from app.board import (
    Db,
    load_board,
    load_card,
    load_column,
    place_card,
    renumber,
    serialize,
)
from app.models import Board, Card, Message, utcnow
from app.schemas import Action, ChatOut, ChatRequest, MessageOut, ModelReply

router = APIRouter(prefix="/api/chat")

# Turns of history replayed to the model. Older messages stay in the database.
HISTORY_LIMIT = 20

# Strict Structured Outputs. Every field is required and nullable rather than
# per-action, because strict mode allows no optional or conditional properties.
RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "board_reply",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["reply", "updates"],
            "properties": {
                "reply": {"type": "string"},
                "updates": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "action",
                            "cardId",
                            "columnId",
                            "title",
                            "details",
                            "position",
                        ],
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": [
                                    "create_card",
                                    "edit_card",
                                    "move_card",
                                    "delete_card",
                                    "rename_column",
                                ],
                            },
                            "cardId": {"type": ["string", "null"]},
                            "columnId": {"type": ["string", "null"]},
                            "title": {"type": ["string", "null"]},
                            "details": {"type": ["string", "null"]},
                            "position": {"type": ["integer", "null"]},
                        },
                    },
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are the assistant inside a Kanban project management app. \
You answer questions about the user's board and make changes to it when asked.

The board as it stands, in the same shape the app uses:

{board}

Columns are ordered as listed; each column's cardIds are in top-to-bottom order.

Put any changes in `updates`, as a list applied in order:

- create_card: columnId, title, and optionally details
- edit_card: cardId, and title and/or details
- move_card: cardId, columnId (the destination, which may be its current column), \
and position (0 is the top; omit for the bottom)
- delete_card: cardId
- rename_column: columnId, title

Use only ids that appear above. Set fields an action does not need to null. When the \
user is asking a question rather than requesting a change, return no updates. \
`reply` is always your message to the user, in plain prose without markdown."""


def resolve(
    loader: Callable[..., Any],
    db: Db,
    user: CurrentUser,
    raw_id: str | None,
    label: str,
) -> Any:
    """Look up an id the model gave. Anything unknown is a bad request, not a 404."""
    if raw_id is None or not raw_id.isdigit():
        raise HTTPException(status_code=400, detail=f"Unknown {label} id: {raw_id!r}")
    try:
        return loader(db, user, int(raw_id))
    except HTTPException as exc:
        raise HTTPException(
            status_code=400, detail=f"Unknown {label} id: {raw_id!r}"
        ) from exc


def require_title(action: Action) -> str:
    title = (action.title or "").strip()
    if not title:
        raise HTTPException(
            status_code=400, detail=f"{action.action} needs a non-empty title"
        )
    return title


def apply_action(db: Db, user: CurrentUser, action: Action) -> None:
    """Apply one action to the session. The caller owns the transaction."""
    match action.action:
        case "create_card":
            column = resolve(load_column, db, user, action.columnId, "column")
            db.add(
                Card(
                    title=require_title(action),
                    details=action.details or "",
                    position=len(column.cards),
                    column=column,
                )
            )
        case "edit_card":
            card = resolve(load_card, db, user, action.cardId, "card")
            if action.title is not None:
                card.title = require_title(action)
            if action.details is not None:
                card.details = action.details
        case "move_card":
            card = resolve(load_card, db, user, action.cardId, "card")
            target = (
                resolve(load_column, db, user, action.columnId, "column")
                if action.columnId is not None
                else card.column
            )
            # No position means the bottom; place_card clamps past-the-end to last.
            position = (
                action.position if action.position is not None else len(target.cards)
            )
            place_card(card, target, position)
        case "delete_card":
            card = resolve(load_card, db, user, action.cardId, "card")
            column = card.column
            remaining = [other for other in column.cards if other.id != card.id]
            db.delete(card)
            renumber(remaining)
        case "rename_column":
            column = resolve(load_column, db, user, action.columnId, "column")
            column.title = require_title(action)


def history_for_model(board: Board) -> list[dict[str, str]]:
    recent = board.messages[-HISTORY_LIMIT:]
    return [{"role": message.role, "content": message.content} for message in recent]


@router.get("/history")
def read_history(db: Db, user: CurrentUser) -> list[MessageOut]:
    board = load_board(db, user)
    return [
        MessageOut(role=message.role, content=message.content)
        for message in board.messages
    ]


@router.post("")
async def chat(body: ChatRequest, db: Db, user: CurrentUser) -> ChatOut:
    board = load_board(db, user)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                board=serialize(board).model_dump_json(indent=2)
            ),
        },
        *history_for_model(board),
        {"role": "user", "content": body.message},
    ]

    content = await ai.complete(messages, response_format=RESPONSE_FORMAT)
    try:
        model_reply = ModelReply.model_validate_json(content)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=502, detail="AI response did not match the expected shape"
        ) from exc

    try:
        for action in model_reply.updates or []:
            apply_action(db, user, action)
    except HTTPException:
        # A bad id anywhere means none of the batch lands, and neither does the turn.
        db.rollback()
        raise

    if model_reply.updates:
        board.updated_at = utcnow()
    db.add(Message(board=board, role="user", content=body.message))
    db.add(Message(board=board, role="assistant", content=model_reply.reply))
    db.commit()

    return ChatOut(reply=model_reply.reply, board=serialize(board))
