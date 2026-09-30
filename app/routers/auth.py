import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.database import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.token import LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS_DETAIL = "Invalid email or password"


def _as_utc(value: datetime) -> datetime:
    """Postgres round-trips `DateTime(timezone=True)` as tz-aware; SQLite
    (used for local dev/tests, since a real Postgres server isn't always
    available) round-trips it naive. Everything is written in UTC, so a
    naive value is always safe to treat as UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _issue_token_pair(user: User, db: Session) -> TokenPair:
    access_token = create_access_token(user.id)
    refresh_token = generate_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            family_id=uuid.uuid4(),
            expires_at=refresh_token_expiry(),
        )
    )
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return _issue_token_pair(user, db)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenPair:
    user = db.query(User).filter(User.email == payload.email).first()
    # Deliberately generic on any failure — never reveal whether the email
    # exists or the password was wrong, which would let an attacker
    # enumerate registered accounts.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS_DETAIL)

    return _issue_token_pair(user, db)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    now = datetime.now(timezone.utc)
    if stored is None or stored.revoked_at is not None or _as_utc(stored.expires_at) < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")

    user = db.get(User, stored.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")

    # Rotate: revoke the presented token and issue a brand new pair, rather
    # than reusing it — keeps a stolen-but-unused refresh token from being
    # replayed indefinitely.
    stored.revoked_at = now
    db.commit()

    return _issue_token_pair(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> None:
    token_hash = hash_refresh_token(payload.refresh_token)
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()
    # No error on an already-revoked/unknown token — logout is idempotent
    # from the client's point of view.
