from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.schemas.user import UserCreate


class DuplicateUserError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


def register_user(db: Session, data: UserCreate) -> User:
    existing = (
        db.query(User)
        .filter((User.username == data.username) | (User.email == data.email))
        .first()
    )
    if existing:
        raise DuplicateUserError("Username or email is already registered.")

    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name or None,
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
