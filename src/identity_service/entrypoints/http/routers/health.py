from fastapi import APIRouter
from fastapi.responses import JSONResponse

from identity_service.entrypoints.http.dependencies.container import ContainerDependency
from identity_service.entrypoints.http.schemas.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(container: ContainerDependency) -> HealthResponse:
    return HealthResponse(status="ok", service=container.settings.service_name)


@router.get("/health/live", response_model=HealthResponse)
async def liveness(container: ContainerDependency) -> HealthResponse:
    return HealthResponse(status="alive", service=container.settings.service_name)


@router.get("/health/ready")
async def readiness(container: ContainerDependency) -> JSONResponse:
    if not await container.readiness_probe.check():
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ready"})
