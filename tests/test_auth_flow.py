import os

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://warranty_app:warranty_dev@localhost:5432/warranty_test",
    ),
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine, make_database_url  # noqa: E402
from app.core.settings import Settings  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

from app.main import app  # noqa: E402

client = TestClient(app)


def test_register_then_login():
    r = client.get("/register")
    assert r.status_code == 200
    assert "Create New User" in r.text

    r = client.post(
        "/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice Example",
            "password": "secret123",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 200

    r = client.post(
        "/login",
        data={"username": "alice", "password": "secret123"},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text

    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Alice Example" in r.text
    assert "alice@example.com" in r.text


def test_duplicate_user_rejected():
    r = client.post(
        "/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice Again",
            "password": "secret123",
        },
    )
    assert r.status_code == 400
    assert "already registered" in r.text


def test_wrong_password_rejected():
    r = client.post(
        "/login",
        data={"username": "alice", "password": "wrongpass"},
    )
    assert r.status_code == 400
    assert "Invalid username or password" in r.text


def test_logout():
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303


def test_login_page_redirects_when_logged_in():
    client.post("/login", data={"username": "alice", "password": "secret123"})
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/dashboard"


def test_health_endpoint_is_public():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_configured_origins():
    allowed = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/health",
        headers={
            "Origin": "https://unlisted.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers


def test_login_sets_session_cookie():
    response = client.post(
        "/login",
        data={"username": "alice", "password": "secret123"},
        follow_redirects=False,
    )

    cookie = response.headers["set-cookie"].lower()
    assert "warranty_session=" in cookie
    assert "samesite=lax" in cookie


def test_postgres_environment_values_build_a_safe_sqlalchemy_url():
    config = Settings(
        DATABASE_URL=None,
        POSTGRES_HOST="postgres.internal",
        POSTGRES_PORT=5432,
        POSTGRES_DB="warranty_portal",
        POSTGRES_USER="warranty_app",
        POSTGRES_PASSWORD="test@password",
    )

    url = make_database_url(config)

    assert url.startswith("postgresql+psycopg2://")
    assert "test%40password" in url


def test_render_style_postgres_url_is_normalized_to_psycopg2():
    config = Settings(
        DATABASE_URL="postgres://warranty_app:test%40password@postgres.internal:5432/warranty_portal"
    )

    url = make_database_url(config)

    assert url.startswith("postgresql+psycopg2://")
    assert "test%40password" in url


def test_non_postgres_url_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="PostgreSQL"):
        make_database_url(Settings(DATABASE_URL="sqlite:///./warranty_portal.db"))


print("ALL TESTS PASSED")
