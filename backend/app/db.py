from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine: Engine
SessionLocal: sessionmaker[Session]


def configure(path: Path) -> None:
    """Point the app at a SQLite file, creating its directory if needed."""
    global engine, SessionLocal

    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")

    # SQLite ignores foreign keys, and so ON DELETE CASCADE, unless this is set
    # on each connection.
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    SessionLocal = sessionmaker(bind=engine)


configure(settings.database_path)


def init_db() -> None:
    """Create the tables if absent and seed the demo user's board once."""
    from app import models  # noqa: F401  - registers the tables on Base.metadata
    from app.seed import seed

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)


def get_db() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
