from typing import Any

from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.account_status import AccountStatus
from identity_service.domain.enums.role import Role
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone


def buyer_to_document(buyer: Buyer) -> dict[str, Any]:
    return {
        "_id": buyer.id.value,
        "full_name": buyer.full_name,
        "email": buyer.email.value,
        "document": buyer.document.value,
        "phone": buyer.phone.value,
        "password_hash": buyer.password_hash,
        "roles": sorted(role.value for role in buyer.roles),
        "status": buyer.status.value,
        "created_at": buyer.created_at,
        "updated_at": buyer.updated_at,
        "version": buyer.version,
    }


def buyer_from_document(document: dict[str, Any]) -> Buyer:
    return Buyer(
        id=BuyerId(document["_id"]),
        full_name=document["full_name"],
        email=Email(document["email"]),
        document=Document(document["document"]),
        phone=Phone(document["phone"]),
        password_hash=document["password_hash"],
        roles=frozenset(Role(role) for role in document["roles"]),
        status=AccountStatus(document["status"]),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
        version=document["version"],
    )
