import json

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

pytestmark = pytest.mark.integration


async def test_jwks_endpoint_exposes_public_key_only(client: httpx.AsyncClient) -> None:
    response = await client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    jwks = response.json()
    assert len(jwks["keys"]) == 1
    jwk = jwks["keys"][0]
    assert set(jwk) == {"kty", "use", "alg", "kid", "n", "e"}
    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    assert isinstance(key, rsa.RSAPublicKey)


async def test_health_endpoints(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json()["status"] == "ok"
    assert (await client.get("/health/live")).json()["status"] == "alive"
    ready = await client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


async def test_metrics_endpoint_exposes_http_metrics(client: httpx.AsyncClient) -> None:
    await client.get("/health")
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


async def test_correlation_id_is_propagated(client: httpx.AsyncClient) -> None:
    correlation_id = "integration-correlation-0001"
    response = await client.get("/health", headers={"X-Correlation-ID": correlation_id})
    assert response.headers["x-correlation-id"] == correlation_id
    generated = await client.get("/health")
    assert generated.headers["x-correlation-id"]


async def test_security_headers_are_present(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


async def test_unknown_route_uses_error_contract(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/unknown")
    assert response.status_code == 404
    body = response.json()
    assert set(body) == {"code", "message", "timestamp", "path", "correlation_id", "field_errors"}


async def test_oversized_request_is_rejected(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        content=b"x" * 10,
        headers={"content-type": "application/json", "content-length": str(10_000_000)},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "REQUEST_BODY_TOO_LARGE"
