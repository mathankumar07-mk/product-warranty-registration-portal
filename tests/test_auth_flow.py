import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

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


print("ALL TESTS PASSED")
