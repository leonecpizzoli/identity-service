from fastapi import APIRouter, Depends

from identity_service.application.dto.commands import LoginCommand, RegisterBuyerCommand
from identity_service.domain.exceptions.errors import DomainError
from identity_service.entrypoints.http.dependencies.auth import (
    enforce_login_rate_limit,
    enforce_register_rate_limit,
)
from identity_service.entrypoints.http.dependencies.container import ContainerDependency
from identity_service.entrypoints.http.schemas.requests import LoginRequest, RegisterBuyerRequest
from identity_service.entrypoints.http.schemas.responses import BuyerResponse, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=201,
    response_model=BuyerResponse,
    dependencies=[Depends(enforce_register_rate_limit)],
)
async def register(payload: RegisterBuyerRequest, container: ContainerDependency) -> BuyerResponse:
    command = RegisterBuyerCommand(
        full_name=payload.full_name,
        email=payload.email,
        document=payload.document,
        phone=payload.phone,
        password=payload.password,
    )
    try:
        output = await container.register_buyer.execute(command)
    except DomainError:
        container.metrics.auth_register_total.labels(result="rejected").inc()
        raise
    container.metrics.auth_register_total.labels(result="created").inc()
    return BuyerResponse.from_output(output)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
async def login(payload: LoginRequest, container: ContainerDependency) -> TokenResponse:
    command = LoginCommand(email=payload.email, password=payload.password)
    try:
        output = await container.authenticate_buyer.execute(command)
    except DomainError:
        container.metrics.auth_login_total.labels(result="rejected").inc()
        raise
    container.metrics.auth_login_total.labels(result="success").inc()
    return TokenResponse.from_output(output)
