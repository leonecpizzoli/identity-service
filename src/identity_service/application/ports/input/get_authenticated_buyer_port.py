from typing import Protocol

from identity_service.application.dto.outputs import BuyerOutput


class GetAuthenticatedBuyerPort(Protocol):
    async def execute(self, buyer_id: str) -> BuyerOutput: ...
