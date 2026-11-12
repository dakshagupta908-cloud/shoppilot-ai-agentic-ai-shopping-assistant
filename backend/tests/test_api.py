import uuid
from types import SimpleNamespace

import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai.errors import APIError
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.seed import seed_products
from app.services import parse_budget

client = TestClient(app)
SESSION = {"X-Session-ID": "test-shopper-01"}


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "")
    monkeypatch.setattr(settings, "ai_api_key", "")
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with test_session() as db:
        seed_products(db)
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Laptop under ₹60k", 60000),
        ("Laptop under ₹60,000", 60000),
        ("Laptop under Rs. 60 thousand", 60000),
        ("Laptop budget 60k", 60000),
        ("Budget ₹45,000; prefer under ₹60k", 60000),
    ],
)
def test_parse_budget_supports_currency_and_thousand_suffix(message, expected):
    assert parse_budget(message) == expected


def test_health_and_seeded_catalogue():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = client.get("/api/products").json()
    assert len(data["products"]) >= 20
    assert {"Laptops", "Smartphones", "Headphones"}.issubset(set(data["categories"]))


def test_product_filtering_and_detail():
    laptops = client.get("/api/products", params={"category": "Laptops", "max_price": 60000}).json()["products"]
    assert laptops
    assert all(item["category"] == "Laptops" and item["price"] <= 60000 for item in laptops)
    product = client.get(f"/api/products/{laptops[0]['id']}")
    assert product.status_code == 200
    assert product.json()["id"] == laptops[0]["id"]
    assert client.get("/api/products/not-a-product").status_code == 404


def test_recommendation_uses_catalogue_and_constraints():
    response = client.post("/api/agent/recommend", json={"message": "Laptop under ₹60,000 with 16GB RAM"})
    assert response.status_code == 200
    result = response.json()
    assert result["recommendations"]
    assert result["requirements"]["max_budget"] == 60000
    assert all(item["product"]["category"] == "Laptops" for item in result["recommendations"])
    assert all(item["product"]["price"] <= 60000 for item in result["recommendations"])
    assert all(int(item["product"]["specifications"]["RAM"].split("GB")[0]) >= 16 for item in result["recommendations"])


def test_cart_server_totals_update_remove_and_invalid_input():
    product = client.get("/api/products").json()["products"][0]
    response = client.post("/api/cart", headers=SESSION, json={"items": [{"product_id": product["id"], "quantity": 2}]})
    assert response.status_code == 200
    cart = response.json()
    assert cart["subtotal"] == product["price"] * 2
    item_id = cart["items"][0]["item_id"]
    updated = client.patch(f"/api/cart/items/{item_id}", headers=SESSION, json={"quantity": 3})
    assert updated.json()["total"] == product["price"] * 3
    assert client.delete(f"/api/cart/items/{item_id}", headers=SESSION).json()["items"] == []
    assert client.post("/api/cart", headers=SESSION, json={"items": [{"product_id": "missing", "quantity": 1}]}).status_code == 404
    assert client.post("/api/cart", headers=SESSION, json={"items": [{"product_id": product["id"], "quantity": 0}]}).status_code == 422


def test_compare_endpoint_returns_actual_products():
    products = client.get("/api/products").json()["products"][:2]
    result = client.post("/api/agent/compare", json={"product_ids": [p["id"] for p in products]})
    assert result.status_code == 200
    assert {p["id"] for p in result.json()["products"]} == {p["id"] for p in products}


def test_checkout_quote_recalculates_server_prices_and_paypal_unconfigured_fails(monkeypatch):
    monkeypatch.setattr(settings, "paypal_client_id", "")
    monkeypatch.setattr(settings, "paypal_client_secret", "")
    products = client.get("/api/products").json()["products"][:2]
    lines = [{"product_id": p["id"], "quantity": 2} for p in products]
    quote = client.post("/api/paypal/quote", json={"items": lines})
    assert quote.status_code == 200
    expected_inr = sum(p["price"] * 2 for p in products)
    assert float(quote.json()["source_amount"]) == expected_inr
    assert quote.json()["currency"] == "USD"
    assert client.post("/api/paypal/create-order", headers=SESSION, json={"items": lines}).status_code == 503


def test_guest_cart_requires_session_and_orders_are_scoped():
    assert client.get("/api/cart").status_code == 400
    assert client.get("/api/orders", headers={"X-Session-ID": "someone-else"}).json()["orders"] == []


def test_gemini_sdk_extracts_structured_requirements_and_keeps_catalogue_grounded(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "test-only-gemini-key")
    monkeypatch.setattr(settings, "ai_model", "gemini-3.1-pro-preview")
    output = (
        '{"category":"Laptops","max_budget_inr":60000,'
        '"minimum_ram_gb":16,"keywords":["programming"]}'
    )

    class FakeInteractions:
        def create(self, **kwargs):
            assert kwargs["model"] == "gemini-3.1-pro-preview"
            assert kwargs["response_format"]["type"] == "text"
            assert kwargs["response_format"]["mime_type"] == "application/json"
            assert "Laptops" in kwargs["response_format"]["schema"]["properties"]["category"]["anyOf"][0]["enum"]
            assert "Customer request:" in kwargs["input"]
            return SimpleNamespace(output_text=output)

    class FakeClient:
        def __init__(self, *, api_key, http_options):
            assert api_key == "test-only-gemini-key"
            assert http_options.timeout == 12_000
            self.interactions = FakeInteractions()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(genai, "Client", FakeClient)
    response = client.post(
        "/api/agent/recommend",
        json={"message": "I need a laptop under ₹60k with 16GB RAM for programming"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "llm_requirements+database"
    assert data["requirements"]["category"] == "Laptops"
    assert data["requirements"]["max_budget"] == 60000
    assert data["requirements"]["minimum_ram_gb"] == 16
    assert data["recommendations"]
    assert all(item["product"]["category"] == "Laptops" for item in data["recommendations"])
    assert all(item["product"]["price"] <= 60000 for item in data["recommendations"])
    assert "test-only-gemini-key" not in response.text


def test_missing_gemini_key_reports_warning_and_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "")
    monkeypatch.setattr(genai, "Client", lambda **kwargs: pytest.fail("Gemini must not be called without a key"))

    response = client.post(
        "/api/agent/recommend",
        json={"message": "Laptop under ₹60k with 16GB RAM"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "database_fallback"
    assert data["requirements"]["max_budget"] == 60000
    assert "AI_API_KEY is missing" in data["ai_warning"]


@pytest.mark.parametrize(
    ("status_code", "warning_fragment"),
    [
        (401, "authentication failed"),
        (404, "model is unavailable"),
        (429, "quota"),
    ],
)
def test_gemini_api_errors_are_sanitized_and_fall_back(monkeypatch, status_code, warning_fragment):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "test-only-gemini-key")

    class FakeInteractions:
        def create(self, **kwargs):
            raise APIError(status_code, {"error": {"message": "private provider response"}})

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.interactions = FakeInteractions()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(genai, "Client", FakeClient)
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Laptop under ₹60k with 16GB RAM"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "database_fallback"
    assert data["requirements"]["max_budget"] == 60000
    assert warning_fragment in data["ai_warning"].lower()
    assert "private provider response" not in response.text


def test_gemini_invalid_structured_output_reports_warning_and_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "test-only-gemini-key")

    class FakeInteractions:
        def create(self, **kwargs):
            return SimpleNamespace(output_text='{"category":"Unknown category"}')

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.interactions = FakeInteractions()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(genai, "Client", FakeClient)
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Laptop under ₹60k"},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "database_fallback"
    assert "invalid requirements response" in response.json()["ai_warning"]
    assert response.json()["requirements"]["max_budget"] == 60000


def test_gemini_transport_error_reports_warning_and_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "test-only-gemini-key")
    request = httpx2.Request("POST", "https://generativelanguage.googleapis.com")

    class FakeInteractions:
        def create(self, **kwargs):
            raise httpx2.ConnectError("mocked network failure", request=request)

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.interactions = FakeInteractions()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(genai, "Client", FakeClient)
    response = client.post(
        "/api/agent/recommend",
        json={"message": "Laptop under ₹60k"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "database_fallback"
    assert "Could not connect to Gemini" in data["ai_warning"]
    assert "mocked network failure" not in response.text


def test_paypal_live_host_is_rejected():
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(paypal_base_url="https://api-m.paypal.com")


def test_mocked_paypal_create_capture_verification_and_duplicate(monkeypatch):
    session_id = f"paypal-test-{uuid.uuid4()}"
    paypal_order_id = f"TEST-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            if url.endswith("/v1/oauth2/token"):
                return httpx.Response(200, json={"access_token": "mock-token"})
            if url.endswith("/v2/checkout/orders"):
                assert kwargs["json"]["purchase_units"][0]["amount"] == {
                    "currency_code": "USD", "value": "695.88",
                }
                return httpx.Response(201, json={"id": paypal_order_id, "status": "CREATED"})
            if url.endswith(f"/v2/checkout/orders/{paypal_order_id}/capture"):
                return httpx.Response(201, json={
                    "id": paypal_order_id,
                    "status": "COMPLETED",
                    "purchase_units": [{
                        "payments": {"captures": [{
                            "id": "CAPTURE-MOCK-01",
                            "status": "COMPLETED",
                            "amount": {"currency_code": "USD", "value": "695.88"},
                        }]},
                    }],
                })
            raise AssertionError(f"Unexpected PayPal request: {url}")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    headers = {"X-Session-ID": session_id}
    payload = {"items": [{"product_id": "lap-01", "quantity": 1}]}
    created = client.post("/api/paypal/create-order", headers=headers, json=payload)
    assert created.status_code == 200
    assert created.json()["id"] == paypal_order_id
    assert created.json()["amount"] == "695.88"

    captured = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert captured.status_code == 200
    assert captured.json()["status"] == "COMPLETED"
    assert captured.json()["paypal_capture_id"] == "CAPTURE-MOCK-01"
    assert captured.json()["items"][0]["unit_price"] == 695.88

    duplicate = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert duplicate.status_code == 200
    assert duplicate.json()["paypal_capture_id"] == "CAPTURE-MOCK-01"
    history = client.get("/api/orders", headers=headers).json()["orders"]
    assert any(order["paypal_order_id"] == paypal_order_id and order["status"] == "COMPLETED" for order in history)


def test_mocked_paypal_capture_rejects_mismatched_amount(monkeypatch):
    session_id = f"paypal-mismatch-{uuid.uuid4()}"
    paypal_order_id = f"TEST-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            if url.endswith("/v1/oauth2/token"):
                return httpx.Response(200, json={"access_token": "mock-token"})
            if url.endswith("/v2/checkout/orders"):
                return httpx.Response(201, json={"id": paypal_order_id, "status": "CREATED"})
            return httpx.Response(201, json={
                "id": paypal_order_id,
                "status": "COMPLETED",
                "purchase_units": [{
                    "payments": {"captures": [{
                        "id": "CAPTURE-MOCK-WRONG",
                        "status": "COMPLETED",
                        "amount": {"currency_code": "USD", "value": "1.00"},
                    }]},
                }],
            })

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    headers = {"X-Session-ID": session_id}
    payload = {"items": [{"product_id": "lap-01", "quantity": 1}]}
    assert client.post("/api/paypal/create-order", headers=headers, json=payload).status_code == 200
    rejected = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert rejected.status_code == 409
    assert "amount or currency" in rejected.json()["detail"]


def test_paypal_cancel_is_idempotent_and_blocks_capture(monkeypatch):
    session_id = f"paypal-cancel-{uuid.uuid4()}"
    paypal_order_id = f"TEST-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            if url.endswith("/v1/oauth2/token"):
                return httpx.Response(200, json={"access_token": "mock-token"})
            if url.endswith("/v2/checkout/orders"):
                return httpx.Response(201, json={"id": paypal_order_id, "status": "CREATED"})
            raise AssertionError("A cancelled order must never be captured.")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    headers = {"X-Session-ID": session_id}
    created = client.post(
        "/api/paypal/create-order",
        headers=headers,
        json={"items": [{"product_id": "lap-01", "quantity": 1}]},
    )
    assert created.status_code == 200

    cancellation = client.post("/api/paypal/cancel-order", headers=headers, json={"order_id": paypal_order_id})
    assert cancellation.status_code == 200
    assert cancellation.json()["status"] == "CANCELLED"
    repeated = client.post("/api/paypal/cancel-order", headers=headers, json={"order_id": paypal_order_id})
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "CANCELLED"
    capture = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert capture.status_code == 409


@pytest.mark.parametrize(
    ("capture_status", "provider_order_status", "expected_status", "expected_http_status"),
    [
        ("PENDING", "PENDING", "PENDING", 200),
        ("DECLINED", "COMPLETED", "FAILED", 409),
    ],
)
def test_paypal_pending_and_declined_capture_states(
    monkeypatch, capture_status, provider_order_status, expected_status, expected_http_status
):
    session_id = f"paypal-state-{uuid.uuid4()}"
    paypal_order_id = f"TEST-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")
    capture_calls = 0

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            nonlocal capture_calls
            if url.endswith("/v1/oauth2/token"):
                return httpx.Response(200, json={"access_token": "mock-token"})
            if url.endswith("/v2/checkout/orders"):
                return httpx.Response(201, json={"id": paypal_order_id, "status": "CREATED"})
            if url.endswith(f"/v2/checkout/orders/{paypal_order_id}/capture"):
                capture_calls += 1
                return httpx.Response(201, json={
                    "id": paypal_order_id,
                    "status": provider_order_status,
                    "purchase_units": [{
                        "payments": {"captures": [{
                            "id": "CAPTURE-MOCK-STATE",
                            "status": capture_status,
                            "amount": {"currency_code": "USD", "value": "695.88"},
                        }]},
                    }],
                })
            raise AssertionError(f"Unexpected PayPal request: {url}")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    headers = {"X-Session-ID": session_id}
    created = client.post(
        "/api/paypal/create-order",
        headers=headers,
        json={"items": [{"product_id": "lap-01", "quantity": 1}]},
    )
    assert created.status_code == 200

    response = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert response.status_code == expected_http_status
    order = client.get("/api/orders", headers=headers).json()["orders"][0]
    assert order["status"] == expected_status
    if expected_status == "PENDING":
        assert order["paypal_capture_id"] == "CAPTURE-MOCK-STATE"

    duplicate = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert duplicate.status_code == 409
    assert capture_calls == 1


def test_paypal_uncertain_capture_is_pending_and_not_retried(monkeypatch):
    session_id = f"paypal-timeout-{uuid.uuid4()}"
    paypal_order_id = f"TEST-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")
    capture_calls = 0

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            nonlocal capture_calls
            if url.endswith("/v1/oauth2/token"):
                return httpx.Response(200, json={"access_token": "mock-token"})
            if url.endswith("/v2/checkout/orders"):
                return httpx.Response(201, json={"id": paypal_order_id, "status": "CREATED"})
            if url.endswith(f"/v2/checkout/orders/{paypal_order_id}/capture"):
                capture_calls += 1
                raise httpx.ReadTimeout("mock timeout")
            raise AssertionError(f"Unexpected PayPal request: {url}")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    headers = {"X-Session-ID": session_id}
    created = client.post(
        "/api/paypal/create-order",
        headers=headers,
        json={"items": [{"product_id": "lap-01", "quantity": 1}]},
    )
    assert created.status_code == 200

    capture = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert capture.status_code == 502
    order = client.get("/api/orders", headers=headers).json()["orders"][0]
    assert order["status"] == "PENDING"
    duplicate = client.post("/api/paypal/capture-order", headers=headers, json={"order_id": paypal_order_id})
    assert duplicate.status_code == 409
    assert capture_calls == 1
