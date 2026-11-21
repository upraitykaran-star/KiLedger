"""API tests run against an isolated in-memory SQLite database."""
import uuid
from contextlib import asynccontextmanager

import pytest
pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
@pytest.fixture
def clients(monkeypatch):
    from backend import main
    from backend.database import init_database
    monkeypatch.setattr(main.settings, "database_url", "sqlite:///:memory:")
    monkeypatch.setattr(main.settings, "allowed_hosts", "localhost,127.0.0.1,testserver")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_database(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(main, "SessionFactory", factory)
    @asynccontextmanager
    async def test_lifespan(_app):
        yield
    monkeypatch.setattr(main.app.router, "lifespan_context", test_lifespan)
    first, second = TestClient(main.app, headers={"host": "localhost"}), TestClient(main.app, headers={"host": "localhost"})
    with first, second:
        yield first, second
    engine.dispose()


def register(client, email):
    response = client.post("/api/v1/auth/register", json={"name": "Tester", "business_name": "Test shop", "email": email, "password": "A-long-test-password-903!"})
    assert response.status_code == 201, response.text
    return response.json()["csrf_token"]


def test_registration_login_and_invalid_password(clients):
    first, _ = clients
    email = f"{uuid.uuid4().hex}@example.com"
    response = first.post("/api/v1/auth/register", json={"name": "Tester", "business_name": "Shop", "email": email, "password": "A-long-test-password-903!"})
    assert response.status_code == 201
    bad = first.post("/api/v1/auth/login", json={"email": email, "password": "incorrect"})
    assert bad.status_code == 401


def test_customers_are_tenant_isolated_and_paginated(clients):
    first, second = clients
    first_csrf = register(first, f"{uuid.uuid4().hex}@example.com")
    second_csrf = register(second, f"{uuid.uuid4().hex}@example.com")
    created = first.post("/api/v1/customers", headers={"X-CSRF-Token": first_csrf}, json={"name": "A customer"})
    assert created.status_code == 201
    customer_id = created.json()["id"]
    assert second.get(f"/api/v1/customers/{customer_id}").status_code == 404
    page = first.get("/api/v1/customers?page=1&page_size=1")
    assert page.status_code == 200 and page.json()["total"] == 1
    assert first.post("/api/v1/customers", json={"name": "Missing CSRF"}).status_code == 403
    assert second_csrf


def test_credit_payment_ledger_and_idempotency(clients):
    first, _ = clients
    csrf = register(first, f"{uuid.uuid4().hex}@example.com")
    customer = first.post("/api/v1/customers", headers={"X-CSRF-Token": csrf}, json={"name": "Ledger customer"}).json()
    entry = {"description": "Credit sale", "amount_minor": 12050, "currency": "INR", "type": "income", "customer_id": customer["id"], "date": "2026-10-28", "method": "UPI", "on_credit": True}
    sale = first.post("/api/v1/transactions", headers={"X-CSRF-Token": csrf, "Idempotency-Key": "sale-1"}, json=entry)
    assert sale.status_code == 201, sale.text
    assert first.post("/api/v1/transactions", headers={"X-CSRF-Token": csrf, "Idempotency-Key": "sale-1"}, json=entry).json()["id"] == sale.json()["id"]
    payment = {**entry, "description": "Part payment", "amount_minor": 2000, "type": "payment", "on_credit": False}
    assert first.post("/api/v1/transactions", headers={"X-CSRF-Token": csrf}, json=payment).status_code == 201
    ledger = first.get(f"/api/v1/customers/{customer['id']}/ledger").json()
    assert ledger["balance_minor"] == 10050
    assert len(ledger["transactions"]) == 2


def test_transaction_validation(clients):
    first, _ = clients
    csrf = register(first, f"{uuid.uuid4().hex}@example.com")
    invalid = {"description": "Zero", "amount_minor": 0, "type": "income", "date": "2026-10-28"}
    assert first.post("/api/v1/transactions", headers={"X-CSRF-Token": csrf}, json=invalid).status_code == 422
    first.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert first.get("/api/v1/customers").status_code == 401
