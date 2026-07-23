from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import jwt
import pytest

pytestmark = pytest.mark.integration

PayloadFactory = Callable[..., dict[str, Any]]

TEST_ISSUER = "https://identity.integration.test"
TEST_AUDIENCE = "vehicle-resale-integration"


async def register_and_login(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
    assert (await client.post("/api/v1/auth/register", json=payload)).status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    result: dict[str, Any] = login.json()
    return result


async def test_me_returns_account_data_without_secrets(
    client: httpx.AsyncClient, make_registration_payload: PayloadFactory
) -> None:
    payload = make_registration_payload()
    login = await register_and_login(client, payload)
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == login["user"]["id"]
    assert body["email"] == payload["email"].lower()
    assert "password" not in response.text
    assert "argon2" not in response.text
    assert payload["document"] not in response.text


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


async def test_me_rejects_malformed_token(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer garbage.token.value"}
    )
    assert response.status_code == 401


async def test_me_rejects_expired_token(
    client: httpx.AsyncClient,
    private_key_pem: str,
    make_registration_payload: PayloadFactory,
) -> None:
    payload = make_registration_payload()
    login = await register_and_login(client, payload)
    issued_at = int(datetime.now(UTC).timestamp()) - 7200
    expired = jwt.encode(
        {
            "sub": login["user"]["id"],
            "roles": ["BUYER"],
            "iss": TEST_ISSUER,
            "aud": TEST_AUDIENCE,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": issued_at + 60,
            "jti": "a" * 32,
        },
        private_key_pem,
        algorithm="RS256",
    )
    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
