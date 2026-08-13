from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User as UserRow
from app.security import verify_password

router = APIRouter(prefix="/api")


class Credentials(BaseModel):
    username: str
    password: str


class User(BaseModel):
    username: str


def require_user(request: Request) -> User:
    """Dependency guarding every /api route except login, logout and health."""
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return User(username=username)


CurrentUser = Annotated[User, Depends(require_user)]


@router.post("/login")
def login(
    credentials: Credentials,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    row = db.scalar(select(UserRow).where(UserRow.username == credentials.username))
    if row is None or not verify_password(credentials.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    request.session["username"] = row.username
    return User(username=row.username)


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "ok"}


@router.get("/me")
def me(user: CurrentUser) -> User:
    return user
