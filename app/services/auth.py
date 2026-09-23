from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate


class DuplicateUserError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def _normalize_username(value: str) -> str:
    return value.strip()


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def register_user(db: Session, data: UserCreate) -> User:
    username = _normalize_username(data.username)
    email = _normalize_email(data.email)

    existing = (
        db.query(User)
        .filter(
            (func.lower(User.username) == username.lower())
            | (func.lower(User.email) == email)
        )
        .first()
    )
    if existing:
        raise DuplicateUserError("Username or email is already registered.")

    user = User(
        username=username,
        email=email,
        full_name=data.full_name.strip() or None,
        hashed_password=hash_password(data.password),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    identifier = username.strip().lower()
    if not identifier:
        raise InvalidCredentialsError("Invalid username or password.")

    user = (
        db.query(User)
        .filter(
            (func.lower(User.username) == identifier)
            | (func.lower(User.email) == identifier)
        )
        .first()
    )
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid username or password.")
    return user
