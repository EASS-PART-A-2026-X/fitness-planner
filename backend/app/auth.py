import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import database as db
from app.models.user import AuthResponse, AuthSession, User, UserPublic
from app.models.workout import WorkoutPlan

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=False)
SESSION_LIFETIME_SECONDS = 30 * 24 * 60 * 60
PASSWORD_ITERATIONS = 310_000
INVALID_CREDENTIALS = "Invalid username or password."


class Credentials(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_.-]+$",
    )
    password: str = Field(min_length=8, max_length=128)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations_raw, salt_hex, digest_hex = stored_hash.split("$")
        iterations = int(iterations_raw)
        expected_digest = bytes.fromhex(digest_hex)
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            iterations,
        )
    except ValueError, TypeError:
        return False

    return hmac.compare_digest(actual_digest, expected_digest)


def _new_session(session: Session, user: User) -> AuthResponse:
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + SESSION_LIFETIME_SECONDS
    db_session = AuthSession(
        user_id=user.id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=expires_at,
    )
    session.add(db_session)
    session.commit()
    return AuthResponse(
        access_token=token,
        expires_in=SESSION_LIFETIME_SECONDS,
        user=UserPublic(id=user.id, username=user.username),
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: db.SessionDep,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    db_session = session.exec(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    ).first()
    if db_session is None or db_session.expires_at <= int(time.time()):
        raise unauthorized

    user = session.get(User, db_session.user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    credentials: Credentials,
    session: db.SessionDep,
) -> AuthResponse:
    username = normalize_username(credentials.username)
    existing_user = session.exec(select(User).where(User.username == username)).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken.",
        )

    highest_workout_user_id = session.exec(select(func.max(WorkoutPlan.user_id))).one()
    highest_account_id = session.exec(select(func.max(User.id))).one()
    user_id = max(highest_workout_user_id or 0, highest_account_id or 0) + 1
    user = User(
        id=user_id,
        username=username,
        password_hash=hash_password(credentials.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if session.exec(select(User).where(User.username == username)).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That username is already taken.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create the account. Please try again.",
        ) from exc
    session.refresh(user)
    return _new_session(session, user)


@router.post("/login", response_model=AuthResponse)
def login(
    credentials: Credentials,
    session: db.SessionDep,
) -> AuthResponse:
    username = normalize_username(credentials.username)
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        hashlib.pbkdf2_hmac(
            "sha256",
            credentials.password.encode(),
            b"\0" * 16,
            PASSWORD_ITERATIONS,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )
    return _new_session(session, user)


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: CurrentUser) -> UserPublic:
    return UserPublic(id=current_user.id, username=current_user.username)


@router.delete("/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    session: db.SessionDep,
) -> None:
    if credentials is None:
        return
    token_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    db_session = session.exec(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    ).first()
    if db_session is not None:
        session.delete(db_session)
        session.commit()
