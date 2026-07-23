from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from identity_service.application.dto.outputs import AuthenticatedPrincipal
from identity_service.domain.exceptions.errors import (
    AuthenticationRequiredError,
    RateLimitExceededError,
)
from identity_service.entrypoints.http.dependencies.container import ContainerDependency

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_principal(
    container: ContainerDependency,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationRequiredError("authentication credentials are required")
    return container.token_verifier.verify(credentials.credentials)


PrincipalDependency = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_login_rate_limit(request: Request, container: ContainerDependency) -> None:
    if not container.login_rate_limiter.allow(_client_key(request)):
        raise RateLimitExceededError("too many login attempts")


def enforce_register_rate_limit(request: Request, container: ContainerDependency) -> None:
    if not container.register_rate_limiter.allow(_client_key(request)):
        raise RateLimitExceededError("too many registration attempts")
