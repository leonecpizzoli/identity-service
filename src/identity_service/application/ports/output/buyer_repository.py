from typing import Protocol

from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.email import Email


class BuyerRepository(Protocol):
    async def insert(self, buyer: Buyer) -> None: ...

    async def find_by_email(self, email: Email) -> Buyer | None: ...

    async def find_by_id(self, buyer_id: BuyerId) -> Buyer | None: ...
