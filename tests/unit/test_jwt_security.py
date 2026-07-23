import base64
import json
from datetime import UTC, datetime, timedelta
from itertools import count

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.role import Role
from identity_service.domain.exceptions.errors import AuthenticationRequiredError
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone
from identity_service.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from identity_service.infrastructure.security.jwt_token_verifier import JwtTokenVerifier
from identity_service.infrastructure.security.rsa_key_set import RsaKeySet

_ISSUER = "https://identity.test"
_AUDIENCE = "platform-test"


def generate_private_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


class FixedClock:
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


class SequentialIdProvider:
    def __init__(self) -> None:
        self._counter = count(1)

    def new_id(self) -> str:
        return f"{next(self._counter):032x}"


@pytest.fixture(scope="module")
def key_set() -> RsaKeySet:
    return RsaKeySet(generate_private_key_pem())


def make_buyer() -> Buyer:
    return Buyer.register(
        buyer_id=BuyerId("b" * 32),
        full_name="Ana Souza",
        email=Email("ana@example.com"),
        document=Document("12345678909"),
        phone=Phone("+5511912345678"),
        password_hash="hashed",
        roles=frozenset({Role.BUYER}),
        now=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
    )


def make_issuer(
    key_set: RsaKeySet, moment: datetime | None = None, ttl_seconds: int = 900
) -> JwtTokenIssuer:
    return JwtTokenIssuer(
        key_set=key_set,
        issuer=_ISSUER,
        audience=_AUDIENCE,
        ttl_seconds=ttl_seconds,
        clock=FixedClock(moment or datetime.now(UTC)),
        id_provider=SequentialIdProvider(),
    )


def test_issued_token_carries_expected_claims(key_set: RsaKeySet) -> None:
    moment = datetime.now(UTC).replace(microsecond=0)
    issued = make_issuer(key_set, moment).issue(make_buyer())
    claims = jwt.decode(
        issued.access_token,
        key=key_set.public_key,
        algorithms=["RS256"],
        issuer=_ISSUER,
        audience=_AUDIENCE,
    )
    assert claims["sub"] == "b" * 32
    assert claims["roles"] == ["BUYER"]
    assert claims["exp"] - claims["iat"] == 900
    assert claims["iat"] == int(moment.timestamp())
    assert claims["jti"]
    header = jwt.get_unverified_header(issued.access_token)
    assert header["alg"] == "RS256"
    assert header["kid"] == key_set.key_id
    assert issued.token_type == "bearer"
    assert issued.expires_in == 900


def test_verifier_accepts_valid_token(key_set: RsaKeySet) -> None:
    issued = make_issuer(key_set).issue(make_buyer())
    verifier = JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience=_AUDIENCE)
    principal = verifier.verify(issued.access_token)
    assert principal.id == "b" * 32
    assert principal.roles == ("BUYER",)


def test_verifier_rejects_expired_token(key_set: RsaKeySet) -> None:
    stale = datetime.now(UTC) - timedelta(hours=2)
    issued = make_issuer(key_set, stale, ttl_seconds=60).issue(make_buyer())
    verifier = JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience=_AUDIENCE)
    with pytest.raises(AuthenticationRequiredError):
        verifier.verify(issued.access_token)


def test_verifier_rejects_wrong_signature(key_set: RsaKeySet) -> None:
    other_key_set = RsaKeySet(generate_private_key_pem())
    issued = make_issuer(other_key_set).issue(make_buyer())
    verifier = JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience=_AUDIENCE)
    with pytest.raises(AuthenticationRequiredError):
        verifier.verify(issued.access_token)


def test_verifier_rejects_wrong_issuer_and_audience(key_set: RsaKeySet) -> None:
    issued = make_issuer(key_set).issue(make_buyer())
    with pytest.raises(AuthenticationRequiredError):
        JwtTokenVerifier(key_set.public_key, issuer="https://evil.test", audience=_AUDIENCE).verify(
            issued.access_token
        )
    with pytest.raises(AuthenticationRequiredError):
        JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience="other-audience").verify(
            issued.access_token
        )


def test_verifier_rejects_tampered_algorithm(key_set: RsaKeySet) -> None:
    verifier = JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience=_AUDIENCE)
    now = int(datetime.now(UTC).timestamp())
    claims = {
        "sub": "b" * 32,
        "roles": ["BUYER"],
        "iss": _ISSUER,
        "aud": _AUDIENCE,
        "iat": now,
        "exp": now + 900,
        "jti": "x" * 32,
    }
    unsigned_header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=")
    unsigned_payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    unsigned_token = b".".join([unsigned_header, unsigned_payload, b""]).decode()
    with pytest.raises(AuthenticationRequiredError):
        verifier.verify(unsigned_token)


def test_verifier_rejects_missing_required_claims(key_set: RsaKeySet) -> None:
    verifier = JwtTokenVerifier(key_set.public_key, issuer=_ISSUER, audience=_AUDIENCE)
    now = int(datetime.now(UTC).timestamp())
    claims = {"sub": "b" * 32, "iss": _ISSUER, "aud": _AUDIENCE, "iat": now, "exp": now + 900}
    token = jwt.encode(claims, key_set.private_key, algorithm="RS256")
    with pytest.raises(AuthenticationRequiredError):
        verifier.verify(token)


def test_jwks_exposes_only_public_material(key_set: RsaKeySet) -> None:
    jwks = key_set.jwks()
    assert len(jwks["keys"]) == 1
    jwk = jwks["keys"][0]
    assert jwk["kty"] == "RSA"
    assert jwk["alg"] == "RS256"
    assert jwk["use"] == "sig"
    assert jwk["kid"] == key_set.key_id
    assert set(jwk) == {"kty", "use", "alg", "kid", "n", "e"}
    restored = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
    assert isinstance(restored, rsa.RSAPublicKey)
    assert restored.public_numbers() == key_set.public_key.public_numbers()


def test_key_id_is_deterministic_per_key(key_set: RsaKeySet) -> None:
    pem = generate_private_key_pem()
    assert RsaKeySet(pem).key_id == RsaKeySet(pem).key_id
    assert RsaKeySet(pem).key_id != key_set.key_id
