from fastapi import APIRouter

from identity_service.entrypoints.http.dependencies.container import ContainerDependency

router = APIRouter(tags=["keys"])


@router.get("/.well-known/jwks.json")
async def get_jwks(container: ContainerDependency) -> dict[str, list[dict[str, str]]]:
    return container.key_set.jwks()
