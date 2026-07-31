from collections.abc import Callable
from typing import Any

import httpx
import jwt
import pytest
from pymongo.asynchronous.database import AsyncDatabase

pytestmark = pytest.mark.integration

TEST_ISSUER = "https://identity.integration.test"
TEST_AUDIENCE = "vehicle-resale-integration"

PayloadFactory = Callable[..., dict[str, Any]]


async def register(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    result: dict[str, Any] = response.json()
    return result


async def test_login_returns_token_and_public_user_data(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    await register(client, payload)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == payload["email"].lower()
    assert "password" not in response.text
    assert "argon2" not in response.text
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == body["user"]["id"]
    assert claims["roles"] == ["BUYER"]
    assert claims["iss"] == TEST_ISSUER
    assert claims["aud"] == TEST_AUDIENCE
    assert {"iat", "exp", "jti", "nbf"} <= set(claims)


async def test_login_rejects_wrong_password(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    await register(client, payload)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "Wr0ngPassword"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_rejects_unknown_email(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "Whatever123"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize("status", ["INACTIVE", "BLOCKED"])
async def test_login_rejects_non_active_account(
    client: httpx.AsyncClient,
    database: AsyncDatabase[dict[str, Any]],
    make_registration_payload: PayloadFactory,
    status: str,
) -> None:
    payload = make_registration_payload()
    created = await register(client, payload)
    await database["buyers"].update_one({"_id": created["id"]}, {"$set": {"status": status}})
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"
