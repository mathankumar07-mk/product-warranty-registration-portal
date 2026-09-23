import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_product_and_claim_workflow():
    client.post(
        "/register",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "full_name": "Bob Example",
            "password": "secret456",
        },
        follow_redirects=False,
    )
    client.post(
        "/login",
        data={"username": "bob", "password": "secret456"},
        follow_redirects=False,
    )

    product_payload = {
        "product_name": "Smart TV",
        "brand": "Acme",
        "model_number": "TV-100",
        "serial_number": "SER-42",
        "purchase_date": "2024-01-15",
        "invoice_number": "INV-1001",
        "warranty_period_months": 24,
    }
    response = client.post("/api/products", json=product_payload)
    assert response.status_code == 201, response.text
    product = response.json()
    assert product["product_name"] == "Smart TV"
    assert product["warranty_expiry_date"]

    claim_response = client.post(
        "/api/claims",
        json={
            "product_id": product["id"],
            "claim_type": "Repair",
            "description": "The display flickers and the TV does not power on reliably.",
        },
    )
    assert claim_response.status_code == 201, claim_response.text
    claim = claim_response.json()
    assert claim["status"] == "pending"
    assert claim["product_id"] == product["id"]

    list_response = client.get("/api/claims")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1
