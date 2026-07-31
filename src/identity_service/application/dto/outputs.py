from dataclasses import dataclass
from datetime import datetime

from identity_service.domain.entities.buyer import Buyer


@dataclass(frozen=True, slots=True)
class BuyerOutput:
    id: str
    full_name: str
    email: str
    document: str
    phone: str
    roles: tuple[str, ...]
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, buyer: Buyer) -> "BuyerOutput":
        return cls(
            id=buyer.id.value,
            full_name=buyer.full_name,
            email=buyer.email.value,
            document=buyer.document.value,
            phone=buyer.phone.value,
            roles=tuple(sorted(role.value for role in buyer.roles)),
            status=buyer.status.value,
            created_at=buyer.created_at,
            updated_at=buyer.updated_at,
        )


@dataclass(frozen=True, slots=True)
class IssuedToken:
    access_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class AccessTokenOutput:
    access_token: str
    token_type: str
    expires_in: int
    user: BuyerOutput


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    id: str
    roles: tuple[str, ...]
