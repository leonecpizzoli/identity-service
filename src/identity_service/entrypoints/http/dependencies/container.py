from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request

from identity_service.application.ports.input.authenticate_buyer_port import AuthenticateBuyerPort
from identity_service.application.ports.input.get_authenticated_buyer_port import (
    GetAuthenticatedBuyerPort,
)
from identity_service.application.ports.input.register_buyer_port import RegisterBuyerPort
from identity_service.infrastructure.observability.health import MongoReadinessProbe
from identity_service.infrastructure.observability.metrics import ServiceMetrics
from identity_service.infrastructure.security.jwt_token_verifier import JwtTokenVerifier
from identity_service.infrastructure.security.rate_limiter import SlidingWindowRateLimiter
from identity_service.infrastructure.security.rsa_key_set import RsaKeySet
from identity_service.infrastructure.settings.config import Settings


@dataclass(frozen=True)
class ApplicationContainer:
    settings: Settings
    metrics: ServiceMetrics
    key_set: RsaKeySet
    token_verifier: JwtTokenVerifier
    readiness_probe: MongoReadinessProbe
    login_rate_limiter: SlidingWindowRateLimiter
    register_rate_limiter: SlidingWindowRateLimiter
    register_buyer: RegisterBuyerPort
    authenticate_buyer: AuthenticateBuyerPort
    get_authenticated_buyer: GetAuthenticatedBuyerPort


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


ContainerDependency = Annotated[ApplicationContainer, Depends(get_container)]
