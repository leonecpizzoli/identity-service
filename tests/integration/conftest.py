import time
from collections.abc import AsyncIterator, Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from identity_service.infrastructure.settings.config import (
    JwtSettings,
    MongoSettings,
    RateLimitSettings,
    Settings,
)
from identity_service.main import create_app

TEST_ISSUER = "https://identity.integration.test"
TEST_AUDIENCE = "vehicle-resale-integration"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def mongo_uri() -> Iterator[str]:
    container = (
        DockerContainer("mongo:8.0")
        .with_command("mongod --replSet rs0 --bind_ip_all")
        .with_exposed_ports(27017)
    )
    container.start()
    wait_for_logs(container, "Waiting for connections", timeout=120)
    container.exec(
        ["mongosh", "--quiet", "--eval", "try { rs.status().ok } catch (e) { rs.initiate().ok }"]
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        _, output = container.exec(["mongosh", "--quiet", "--eval", "db.hello().isWritablePrimary"])
        if b"true" in output:
            break
        time.sleep(0.5)
    else:
        container.stop()
        raise RuntimeError("mongodb replica set did not elect a primary")
    host = container.get_container_host_ip()
    port = container.get_exposed_port(27017)
    yield f"mongodb://{host}:{port}/?directConnection=true"
    container.stop()


@pytest.fixture(scope="session")
def private_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


@pytest.fixture
def settings(mongo_uri: str, private_key_pem: str) -> Settings:
    return Settings(
        environment="test",
        mongo=MongoSettings(uri=mongo_uri, database=f"identity_test_{uuid4().hex[:12]}"),
        jwt=JwtSettings(
            private_key_pem=private_key_pem,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
            access_token_ttl_seconds=900,
        ),
        rate_limit=RateLimitSettings(login_limit=1000, register_limit=1000),
    )


@pytest.fixture
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as http_client:
            yield http_client


@pytest.fixture
async def database(settings: Settings) -> AsyncIterator[AsyncDatabase[dict[str, Any]]]:
    mongo_client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(
        settings.mongo.uri, tz_aware=True
    )
    yield mongo_client[settings.mongo.database]
    await mongo_client.close()


def registration_payload(**overrides: Any) -> dict[str, Any]:
    unique = uuid4().hex[:10]
    payload: dict[str, Any] = {
        "full_name": "Ana Souza",
        "email": f"ana.{unique}@example.com",
        "document": f"DOC{unique.upper()}",
        "phone": "+5511912345678",
        "password": "Str0ngPassword",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def make_registration_payload() -> Any:
    return registration_payload
