import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin, auth
from app.core.database import Base, SessionLocal, engine
from app.core.settings import settings
import app.models  # noqa: F401  (registers all models)

logger = logging.getLogger("warranty_portal")

TABLES_READY = False


def init_db() -> bool:
    """Create missing tables without deleting data. Returns True on success."""
    global TABLES_READY
    try:
        Base.metadata.create_all(bind=engine)
        TABLES_READY = True
        return True
    except Exception as exc:  # never crash import/startup on DB outage
        logger.warning("Database init failed (tables may already exist): %s", exc)
        return False


def bootstrap_admin() -> None:
    """Promote INITIAL_ADMIN_EMAIL to admin on first startup if no admin exists.

    No passwords are hardcoded. The account must already exist (created via
    /register). Runs only when INITIAL_ADMIN_EMAIL is set.
    """
    email = (settings.INITIAL_ADMIN_EMAIL or "").strip().lower()
    if not email:
        return
    try:
        db = SessionLocal()
        try:
            admins = (
                db.query(func.count(app.models.User.id))
                .filter(app.models.User.role == "admin")
                .scalar()
                or 0
            )
            if admins > 0:
                return
            user = (
                db.query(app.models.User)
                .filter(func.lower(app.models.User.email) == email)
                .first()
            )
            if not user:
                logger.warning(
                    "INITIAL_ADMIN_EMAIL set but no such user: %s", email
                )
                return
            user.role = "admin"
            db.commit()
            logger.warning("Promoted %s to admin via INITIAL_ADMIN_EMAIL.", email)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Admin bootstrap failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if init_db():
        bootstrap_admin()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

cors_origins = [
    origin.strip().rstrip("/")
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]
if "*" in cors_origins:
    raise ValueError("CORS_ORIGINS must contain explicit origins, not '*'.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE,
    same_site=settings.SESSION_COOKIE_SAMESITE,
    https_only=settings.SESSION_COOKIE_SECURE,
)

app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
def readiness_check():
    if not TABLES_READY:
        # Try once more; helps Render recover without restart.
        init_db()
    return {"status": "ok" if TABLES_READY else "degraded"}
