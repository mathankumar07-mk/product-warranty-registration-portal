"""Shared authentication dependencies.

Reuses the existing session-cookie mechanism (``request.session["username"]``)
and the ``User.role`` column. The role is always read from PostgreSQL, never
from the request body or cookies.
"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User


def get_logged_in_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    username = request.session.get("username")
    if not username:
        return None
    normalized = str(username).strip()
    if not normalized:
        return None
    return (
        db.query(User)
        .filter(func.lower(User.username) == normalized.lower())
        .first()
    )


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    user = get_logged_in_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_current_admin(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """Require an authenticated user whose DB role is exactly ``admin``."""
    user = get_logged_in_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Re-read role from DB state; never trust client-supplied role.
    db.refresh(user)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
