from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.settings import Settings, settings


def normalize_postgres_url(url_str: str) -> str:
    """Accept Render-style ``postgres://`` / plain ``postgresql://`` URLs and
    return a SQLAlchemy URL string pinned to the ``psycopg2`` driver with
    reserved characters in the password correctly escaped."""
    if url_str.startswith("postgres://"):
        url_str = "postgresql+psycopg2://" + url_str[len("postgres://"):]
    elif url_str.startswith("postgresql://"):
        url_str = "postgresql+psycopg2://" + url_str[len("postgresql://"):]
    try:
        parsed = make_url(url_str)
    except Exception as exc:
        raise ValueError(f"Invalid DATABASE_URL: {exc}") from exc
    if parsed.drivername != "postgresql+psycopg2":
        raise ValueError("DATABASE_URL must be a PostgreSQL URL.")
    return parsed.render_as_string(hide_password=False)


def make_database_url(config: Settings) -> str:
    if config.DATABASE_URL:
        return normalize_postgres_url(config.DATABASE_URL)

    return URL.create(
        "postgresql+psycopg2",
        username=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        database=config.POSTGRES_DB,
    ).render_as_string(hide_password=False)


database_url = make_database_url(settings)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
