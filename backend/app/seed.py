from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Board, BoardColumn, Card, User
from app.security import hash_password

DEMO_USERNAME = "user"
DEMO_PASSWORD = "password"
BOARD_TITLE = "Kanban Studio"

# The five demo columns and their cards, mirroring frontend/src/lib/kanban.ts.
DEMO_COLUMNS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Backlog",
        [
            (
                "Align roadmap themes",
                "Draft quarterly themes with impact statements and metrics.",
            ),
            (
                "Gather customer signals",
                "Review support tags, sales notes, and churn feedback.",
            ),
        ],
    ),
    (
        "Discovery",
        [
            (
                "Prototype analytics view",
                "Sketch initial dashboard layout and key drill-downs.",
            )
        ],
    ),
    (
        "In Progress",
        [
            (
                "Refine status language",
                "Standardize column labels and tone across the board.",
            ),
            (
                "Design card layout",
                "Add hierarchy and spacing for scanning dense lists.",
            ),
        ],
    ),
    ("Review", [("QA micro-interactions", "Verify hover, focus, and loading states.")]),
    (
        "Done",
        [
            ("Ship marketing page", "Final copy approved and asset pack delivered."),
            ("Close onboarding sprint", "Document release notes and share internally."),
        ],
    ),
]


def seed(session: Session) -> None:
    """Create the demo user and their board. Keyed on the user, so it runs once."""
    existing = session.scalar(select(User).where(User.username == DEMO_USERNAME))
    if existing:
        return

    user = User(username=DEMO_USERNAME, password_hash=hash_password(DEMO_PASSWORD))
    board = Board(title=BOARD_TITLE, user=user)
    board.columns = [
        BoardColumn(
            title=title,
            position=column_position,
            cards=[
                Card(title=card_title, details=details, position=card_position)
                for card_position, (card_title, details) in enumerate(cards)
            ],
        )
        for column_position, (title, cards) in enumerate(DEMO_COLUMNS)
    ]

    session.add(user)
    session.commit()
