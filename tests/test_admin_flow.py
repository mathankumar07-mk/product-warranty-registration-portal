"""Admin section tests: auth, stats, product/claim management, regressions."""

import os
import re

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://warranty_app:warranty_dev@localhost:5432/warranty_test",
    ),
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

from app.main import app  # noqa: E402

admin_client = TestClient(app)
customer_client = TestClient(app)
anon_client = TestClient(app)


def _register(client: TestClient, username: str, email: str, password: str = "secret123"):
    r = client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "full_name": f"{username} Full",
            "password": password,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text


def _login(client: TestClient, username: str, password: str = "secret123"):
    r = client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text


def _promote_to_admin(username: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        user.role = "admin"
        db.commit()
    finally:
        db.close()


def _csrf(client: TestClient, url: str) -> str:
    r = client.get(url)
    assert r.status_code == 200, r.text
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m, "CSRF token not found in " + url
    return m.group(1)


def setup_module():
    _register(admin_client, "admin_user", "admin_user@example.com")
    _register(customer_client, "cust_user", "cust_user@example.com")
    _promote_to_admin("admin_user")
    # Re-login admin so session reflects promoted role (session stores username only,
    # role is re-read from DB per request, but re-login keeps it clean).
    _login(admin_client, "admin_user")
    _login(customer_client, "cust_user")


def test_admin_dashboard_allowed():
    r = admin_client.get("/admin/dashboard")
    assert r.status_code == 200, r.text
    assert "Admin Dashboard" in r.text
    assert "Total customers" in r.text


def test_admin_stats_from_db():
    r = admin_client.get("/api/admin/stats")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_customers"] >= 1  # cust_user (+ others from other test files)
    assert data["total_products"] >= 0
    assert data["total_claims"] >= 0


def test_customer_denied_admin_html():
    r = customer_client.get("/admin/dashboard", follow_redirects=False)
    assert r.status_code in (403, 303), r.text
    if r.status_code == 303:
        assert "/login" in r.headers.get("location", "") or "/dashboard" in r.headers.get(
            "location", ""
        )


def test_customer_denied_admin_api():
    r = customer_client.get("/api/admin/stats")
    assert r.status_code == 403, r.text


def test_unauthenticated_denied():
    r = anon_client.get("/api/admin/stats")
    assert r.status_code == 401, r.text
    r = anon_client.get("/admin/dashboard", follow_redirects=False)
    assert r.status_code == 303, r.text
    assert "/login" in r.headers.get("location", "")


def test_public_registration_cannot_create_admin():
    r = anon_client.post(
        "/register",
        data={
            "username": "sneaky",
            "email": "sneaky@example.com",
            "full_name": "Sneaky",
            "password": "secret123",
            "role": "admin",  # must be ignored (extra field / no such input)
        },
        follow_redirects=False,
    )
    assert r.status_code in (303, 400, 422), r.text
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "sneaky").first()
        assert user is not None
        assert user.role == "customer"
    finally:
        db.close()


def test_customer_list_no_password_hashes():
    r = admin_client.get("/api/admin/customers")
    assert r.status_code == 200, r.text
    for item in r.json():
        assert "hashed_password" not in item
        assert "id" in item and "username" in item and "email" in item
    # Pagination works
    r = admin_client.get("/api/admin/customers?page=1&page_size=1")
    assert r.status_code == 200
    assert len(r.json()) <= 1
    # Customer cannot list
    r = customer_client.get("/api/admin/customers")
    assert r.status_code == 403


def test_product_management_authorization():
    # Customer creates a product
    payload = {
        "product_name": "Washer",
        "brand": "Acme",
        "purchase_date": "2024-02-01",
        "invoice_number": "INV-ADMIN-1",
        "warranty_period_months": 12,
    }
    r = customer_client.post("/api/products", json=payload)
    assert r.status_code == 201, r.text
    product_id = r.json()["id"]

    # Customer cannot use admin API
    r = customer_client.patch(
        f"/api/admin/products/{product_id}",
        json={
            "product_name": "Washer X",
            "brand": "Acme",
            "purchase_date": "2024-02-01",
            "invoice_number": "INV-ADMIN-1",
            "warranty_period_months": 12,
            "status": "expired",
        },
    )
    assert r.status_code == 403, r.text

    # Admin can update
    r = admin_client.patch(
        f"/api/admin/products/{product_id}",
        json={
            "product_name": "Washer X",
            "brand": "Acme",
            "purchase_date": "2024-02-01",
            "invoice_number": "INV-ADMIN-1",
            "warranty_period_months": 12,
            "status": "expired",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "expired"

    # Unauthenticated cannot update
    r = anon_client.patch(
        f"/api/admin/products/{product_id}",
        json={
            "product_name": "Washer Y",
            "brand": "Acme",
            "purchase_date": "2024-02-01",
            "invoice_number": "INV-ADMIN-1",
            "warranty_period_months": 12,
            "status": "active",
        },
    )
    assert r.status_code == 401, r.text

    # Admin can delete
    r = admin_client.delete(f"/api/admin/products/{product_id}")
    assert r.status_code == 204, r.text


def test_claim_approval_authorization():
    # Customer creates product + claim
    r = customer_client.post(
        "/api/products",
        json={
            "product_name": "Fridge",
            "brand": "Acme",
            "purchase_date": "2024-03-01",
            "invoice_number": "INV-ADMIN-2",
            "warranty_period_months": 12,
        },
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = customer_client.post(
        "/api/claims",
        json={
            "product_id": pid,
            "claim_type": "Repair",
            "description": "The fridge does not cool below ten degrees at all.",
        },
    )
    assert r.status_code == 201, r.text
    claim_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    # Customer cannot approve
    r = customer_client.patch(
        f"/api/admin/claims/{claim_id}", json={"status": "approved"}
    )
    assert r.status_code in (401, 403, 404), r.text

    # Admin approves
    r = admin_client.patch(
        f"/api/admin/claims/{claim_id}", json={"status": "approved"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # Invalid transition (approved -> rejected) rejected
    r = admin_client.patch(
        f"/api/admin/claims/{claim_id}", json={"status": "rejected"}
    )
    assert r.status_code == 400, r.text

    # Second claim for rejection path
    r = customer_client.post(
        "/api/claims",
        json={
            "product_id": pid,
            "claim_type": "Repair",
            "description": "The freezer makes a loud grinding noise every hour.",
        },
    )
    assert r.status_code == 201, r.text
    claim2 = r.json()["id"]
    r = admin_client.patch(
        f"/api/admin/claims/{claim2}", json={"status": "rejected"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"


def test_admin_html_csrf_protected():
    token = _csrf(admin_client, "/admin/products")
    # Missing token -> 422 (FastAPI form validation) or 403
    r = admin_client.post("/admin/claims/99999/approve", data={})
    assert r.status_code in (403, 422), r.text
    # Wrong token -> 403
    r = admin_client.post(
        "/admin/claims/99999/approve", data={"csrf_token": "wrong"}
    )
    assert r.status_code == 403, r.text
    assert token  # token extraction worked


def test_existing_customer_flows_still_work():
    # Dashboard renders for customer
    r = customer_client.get("/dashboard")
    assert r.status_code == 200, r.text
    assert "cust_user@example.com" in r.text
    # Customer API still scoped to own data
    r = customer_client.get("/api/products")
    assert r.status_code == 200
    # Health still public
    r = anon_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
