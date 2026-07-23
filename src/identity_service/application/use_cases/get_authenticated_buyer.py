from identity_service.application.dto.outputs import BuyerOutput
from identity_service.application.ports.output.buyer_repository import BuyerRepository
from identity_service.domain.exceptions.errors import BuyerNotFoundError
from identity_service.domain.value_objects.buyer_id import BuyerId


class GetAuthenticatedBuyer:
    def __init__(self, repository: BuyerRepository) -> None:
        self._repository = repository

    async def execute(self, buyer_id: str) -> BuyerOutput:
        buyer = await self._repository.find_by_id(BuyerId(buyer_id))
        if buyer is None:
            raise BuyerNotFoundError("buyer account not found")
        return BuyerOutput.from_entity(buyer)
