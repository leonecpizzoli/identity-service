from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from identity_service.entrypoints.http.dependencies.container import ContainerDependency

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics(container: ContainerDependency) -> Response:
    return Response(
        content=generate_latest(container.metrics.registry),
        media_type=CONTENT_TYPE_LATEST,
    )
