import jwt

from identity_service.application.dto.outputs import IssuedToken
from identity_service.application.ports.output.clock import Clock
from identity_service.application.ports.output.id_provider import IdProvider
from identity_service.domain.entities.buyer import Buyer
from identity_service.infrastructure.security.rsa_key_set import RsaKeySet

_BEARER_SCHEME = "bearer"


class JwtTokenIssuer:
    def __init__(
        self,
        key_set: RsaKeySet,
        issuer: str,
        audience: str,
        ttl_seconds: int,
        clock: Clock,
        id_provider: IdProvider,
    ) -> None:
        self._key_set = key_set
        self._issuer = issuer
        self._audience = audience
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._id_provider = id_provider

    def issue(self, buyer: Buyer) -> IssuedToken:
        issued_at = int(self._clock.now().timestamp())
        claims = {
            "sub": buyer.id.value,
            "roles": sorted(role.value for role in buyer.roles),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": issued_at + self._ttl_seconds,
            "jti": self._id_provider.new_id(),
        }
        access_token = jwt.encode(
            claims,
            self._key_set.private_key,
            algorithm="RS256",
            headers={"kid": self._key_set.key_id},
        )
        return IssuedToken(
            access_token=access_token,
            token_type=_BEARER_SCHEME,
            expires_in=self._ttl_seconds,
        )
