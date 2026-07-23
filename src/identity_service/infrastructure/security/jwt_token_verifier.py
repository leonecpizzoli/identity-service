import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from identity_service.application.dto.outputs import AuthenticatedPrincipal
from identity_service.domain.exceptions.errors import AuthenticationRequiredError

_REQUIRED_CLAIMS = ["sub", "exp", "iat", "iss", "aud", "jti"]


class JwtTokenVerifier:
    def __init__(self, public_key: rsa.RSAPublicKey, issuer: str, audience: str) -> None:
        self._public_key = public_key
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> AuthenticatedPrincipal:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise AuthenticationRequiredError("token algorithm is not allowed")
            claims = jwt.decode(
                token,
                key=self._public_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.InvalidTokenError as error:
            raise AuthenticationRequiredError("token is invalid or expired") from error
        subject = claims.get("sub")
        raw_roles = claims.get("roles")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationRequiredError("token subject is invalid")
        if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
            raise AuthenticationRequiredError("token roles are invalid")
        return AuthenticatedPrincipal(id=subject, roles=tuple(sorted(raw_roles)))
