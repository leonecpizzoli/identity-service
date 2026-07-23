import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from identity_service.domain.exceptions.errors import (
    AccountNotActiveError,
    AuthenticationRequiredError,
    BuyerNotFoundError,
    DocumentAlreadyRegisteredError,
    DomainError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RateLimitExceededError,
    RegistrationConflictError,
    ValidationError,
)
from identity_service.entrypoints.http.schemas.errors import ErrorResponse, FieldErrorItem
from identity_service.infrastructure.observability.correlation import current_correlation_id
from identity_service.infrastructure.observability.metrics import ServiceMetrics

_logger = logging.getLogger("identity_service.errors")

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    ValidationError: 422,
    InvalidCredentialsError: 401,
    AuthenticationRequiredError: 401,
    AccountNotActiveError: 403,
    EmailAlreadyRegisteredError: 409,
    DocumentAlreadyRegisteredError: 409,
    RegistrationConflictError: 409,
    BuyerNotFoundError: 404,
    RateLimitExceededError: 429,
}


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    field_errors: list[FieldErrorItem] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        code=code,
        message=message,
        timestamp=datetime.now(UTC),
        path=request.url.path,
        correlation_id=current_correlation_id(),
        field_errors=field_errors or [],
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _resolve_status(error: DomainError) -> int:
    for error_type, status_code in _STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI, metrics: ServiceMetrics) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        status_code = _resolve_status(error)
        if status_code == 409:
            metrics.conflicts_total.labels(code=error.code).inc()
        if status_code >= 400:
            metrics.http_errors_total.labels(code=error.code).inc()
        field_errors: list[FieldErrorItem] = []
        if isinstance(error, ValidationError) and error.field:
            field_errors = [FieldErrorItem(field=error.field, message=error.message)]
        return _error_response(request, status_code, error.code, error.message, field_errors)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        metrics.http_errors_total.labels(code="REQUEST_VALIDATION_ERROR").inc()
        field_errors = [
            FieldErrorItem(
                field=".".join(str(part) for part in item["loc"][1:]) or str(item["loc"][0]),
                message=str(item["msg"]),
            )
            for item in error.errors()
        ]
        return _error_response(
            request,
            422,
            "REQUEST_VALIDATION_ERROR",
            "request payload is invalid",
            field_errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if error.status_code == 404 else f"HTTP_{error.status_code}"
        metrics.http_errors_total.labels(code=code).inc()
        return _error_response(request, error.status_code, code, str(error.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        _logger.error("unhandled_error", exc_info=(type(error), error, error.__traceback__))
        metrics.http_errors_total.labels(code="INTERNAL_ERROR").inc()
        return _error_response(request, 500, "INTERNAL_ERROR", "an unexpected error occurred")
