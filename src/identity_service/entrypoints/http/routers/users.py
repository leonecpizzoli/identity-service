from fastapi import APIRouter

from identity_service.entrypoints.http.dependencies.auth import PrincipalDependency
from identity_service.entrypoints.http.dependencies.container import ContainerDependency
from identity_service.entrypoints.http.schemas.responses import BuyerResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=BuyerResponse)
async def get_me(principal: PrincipalDependency, container: ContainerDependency) -> BuyerResponse:
    output = await container.get_authenticated_buyer.execute(principal.id)
    return BuyerResponse.from_output(output)
