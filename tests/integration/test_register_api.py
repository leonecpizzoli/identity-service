import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.integration

PayloadFactory = Callable[..., dict[str, Any]]


async def test_register_creates_buyer(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == payload["email"].lower()
    assert body["roles"] == ["BUYER"]
    assert body["status"] == "ACTIVE"
    assert body["id"]
    assert "password" not in response.text
    assert "argon2" not in response.text
    assert body["document"].startswith("***")


async def test_register_rejects_duplicate_email(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/auth/register",
        json=make_registration_payload(email=payload["email"]),
    )
    assert second.status_code == 409
    assert second.json()["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_register_rejects_duplicate_document(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    second = await client.post(
        "/api/v1/auth/register",
        json=make_registration_payload(document=payload["document"]),
    )
    assert second.status_code == 409
    assert second.json()["code"] == "DOCUMENT_ALREADY_REGISTERED"


async def test_concurrent_registrations_with_same_email_create_single_account(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    email = make_registration_payload()["email"]
    payloads = [make_registration_payload(email=email) for _ in range(6)]
    responses = await asyncio.gather(
        *(client.post("/api/v1/auth/register", json=payload) for payload in payloads)
    )
    status_codes = sorted(response.status_code for response in responses)
    assert status_codes.count(201) == 1
    assert all(code in (201, 409) for code in status_codes)


async def test_register_rejects_weak_password(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    response = await client.post(
        "/api/v1/auth/register", json=make_registration_payload(password="weakpass")
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["field_errors"][0]["field"] == "password"


async def test_register_rejects_unknown_fields(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    payload["role"] = "ADMIN"
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


async def test_register_error_contract_shape(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    response = await client.post(
        "/api/v1/auth/register", json=make_registration_payload(email="broken")
    )
    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"code", "message", "timestamp", "path", "correlation_id", "field_errors"}
    assert body["path"] == "/api/v1/auth/register"
