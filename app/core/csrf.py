"""CSRF protection for cookie-session HTML forms.

Uses the existing Starlette session (signed cookie) to store a per-session
token. No extra dependencies or secrets needed.
"""

import secrets

from fastapi import HTTPException, Request

CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Return the session CSRF token, creating one if missing."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token or not isinstance(token, str):
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(request: Request, submitted: str | None) -> None:
    """Raise 403 if the submitted token does not match the session token."""
    expected = request.session.get(CSRF_SESSION_KEY)
    if not expected or not submitted:
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")
    if not secrets.compare_digest(str(submitted), str(expected)):
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")
