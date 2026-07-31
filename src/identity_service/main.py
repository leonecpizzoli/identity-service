from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CollectorRegistry

from identity_service.application.use_cases.authenticate_buyer import AuthenticateBuyer
from identity_service.application.use_cases.get_authenticated_buyer import GetAuthenticatedBuyer
from identity_service.application.use_cases.register_buyer import RegisterBuyer
from identity_service.entrypoints.http.dependencies.container import ApplicationContainer
from identity_service.entrypoints.http.exception_handlers.handlers import (
    register_exception_handlers,
)
from identity_service.entrypoints.http.middleware.body_limit import RequestBodyLimitMiddleware
from identity_service.entrypoints.http.middleware.correlation import CorrelationIdMiddleware
from identity_service.entrypoints.http.middleware.metrics import HttpMetricsMiddleware
from identity_service.entrypoints.http.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from identity_service.entrypoints.http.routers import auth, health, keys, users
from identity_service.entrypoints.http.routers import metrics as metrics_router
from identity_service.infrastructure.bootstrap import ensure_bootstrap_admin
from identity_service.infrastructure.observability.health import MongoReadinessProbe
from identity_service.infrastructure.observability.logging_setup import configure_logging
from identity_service.infrastructure.observability.metrics import ServiceMetrics
from identity_service.infrastructure.persistence.mongodb.client import create_mongo_client
from identity_service.infrastructure.persistence.mongodb.indexes import ensure_buyer_indexes
from identity_service.infrastructure.persistence.mongodb.mongo_buyer_repository import (
    MongoBuyerRepository,
)
from identity_service.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from identity_service.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from identity_service.infrastructure.security.jwt_token_verifier import JwtTokenVerifier
from identity_service.infrastructure.security.rate_limiter import SlidingWindowRateLimiter
from identity_service.infrastructure.security.rsa_key_set import RsaKeySet
from identity_service.infrastructure.settings.config import Settings
from identity_service.infrastructure.system.clock import UtcClock
from identity_service.infrastructure.system.id_provider import Uuid4IdProvider


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    metrics = ServiceMetrics(CollectorRegistry())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log_listener = configure_logging(app_settings.logging.level)
        key_set = RsaKeySet(app_settings.jwt.require_private_key_pem())
        mongo_client = create_mongo_client(app_settings.mongo)
        try:
            database = mongo_client[app_settings.mongo.database]
            buyers = database["buyers"]
            await ensure_buyer_indexes(buyers)
            repository = MongoBuyerRepository(buyers)
            password_hasher = Argon2PasswordHasher()
            clock = UtcClock()
            id_provider = Uuid4IdProvider()
            token_issuer = JwtTokenIssuer(
                key_set=key_set,
                issuer=app_settings.jwt.issuer,
                audience=app_settings.jwt.audience,
                ttl_seconds=app_settings.jwt.access_token_ttl_seconds,
                clock=clock,
                id_provider=id_provider,
            )
            await ensure_bootstrap_admin(
                app_settings.bootstrap, repository, password_hasher, clock, id_provider
            )
            app.state.container = ApplicationContainer(
                settings=app_settings,
                metrics=metrics,
                key_set=key_set,
                token_verifier=JwtTokenVerifier(
                    public_key=key_set.public_key,
                    issuer=app_settings.jwt.issuer,
                    audience=app_settings.jwt.audience,
                ),
                readiness_probe=MongoReadinessProbe(mongo_client),
                login_rate_limiter=SlidingWindowRateLimiter(
                    app_settings.rate_limit.login_limit,
                    app_settings.rate_limit.window_seconds,
                ),
                register_rate_limiter=SlidingWindowRateLimiter(
                    app_settings.rate_limit.register_limit,
                    app_settings.rate_limit.window_seconds,
                ),
                register_buyer=RegisterBuyer(repository, password_hasher, clock, id_provider),
                authenticate_buyer=AuthenticateBuyer(repository, password_hasher, token_issuer),
                get_authenticated_buyer=GetAuthenticatedBuyer(repository),
            )
            yield
        finally:
            await mongo_client.close()
            log_listener.stop()

    app = FastAPI(title="identity-service", version="1.0.0", lifespan=lifespan)
    app.add_middleware(HttpMetricsMiddleware, metrics=metrics)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=app_settings.security.max_request_body_bytes,
    )
    app.add_middleware(CorrelationIdMiddleware)
    if app_settings.cors.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.cors.allowed_origins,
            allow_methods=app_settings.cors.allowed_methods,
            allow_headers=app_settings.cors.allowed_headers,
            allow_credentials=app_settings.cors.allow_credentials,
        )
    register_exception_handlers(app, metrics)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(keys.router)
    app.include_router(health.router)
    app.include_router(metrics_router.router)
    return app


app = create_app()
