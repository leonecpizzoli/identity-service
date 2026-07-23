from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.exceptions.errors import (
    DocumentAlreadyRegisteredError,
    DomainError,
    EmailAlreadyRegisteredError,
    RegistrationConflictError,
)
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.email import Email
from identity_service.infrastructure.persistence.mongodb.buyer_documents import (
    buyer_from_document,
    buyer_to_document,
)


class MongoBuyerRepository:
    def __init__(self, collection: AsyncCollection[dict[str, Any]]) -> None:
        self._collection = collection

    async def insert(self, buyer: Buyer) -> None:
        try:
            await self._collection.insert_one(buyer_to_document(buyer))
        except DuplicateKeyError as error:
            raise _translate_duplicate(error) from error

    async def find_by_email(self, email: Email) -> Buyer | None:
        document = await self._collection.find_one({"email": email.value})
        return buyer_from_document(document) if document else None

    async def find_by_id(self, buyer_id: BuyerId) -> Buyer | None:
        document = await self._collection.find_one({"_id": buyer_id.value})
        return buyer_from_document(document) if document else None


def _translate_duplicate(error: DuplicateKeyError) -> DomainError:
    message = str(error.details.get("errmsg", "")) if error.details else ""
    if "ux_buyers_email" in message:
        return EmailAlreadyRegisteredError("email is already registered")
    if "ux_buyers_document" in message:
        return DocumentAlreadyRegisteredError("document is already registered")
    return RegistrationConflictError("registration conflicts with an existing account")
