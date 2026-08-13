from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

# The MVP has one hardcoded account. Part 6 replaces this with a users table lookup.
DEMO_USERNAME = "user"
DEMO_PASSWORD = "password"

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
def login(credentials: Credentials, request: Request) -> User:
    if credentials.username != DEMO_USERNAME or credentials.password != DEMO_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    request.session["username"] = credentials.username
    return User(username=credentials.username)


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "ok"}


@router.get("/me")
def me(user: CurrentUser) -> User:
    return user
