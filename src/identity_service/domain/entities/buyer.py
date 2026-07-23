from dataclasses import dataclass
from datetime import datetime

from identity_service.domain.enums.account_status import AccountStatus
from identity_service.domain.enums.role import Role
from identity_service.domain.exceptions.errors import AccountNotActiveError, ValidationError
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone


@dataclass(slots=True)
class Buyer:
    id: BuyerId
    full_name: str
    email: Email
    document: Document
    phone: Phone
    password_hash: str
    roles: frozenset[Role]
    status: AccountStatus
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def register(
        cls,
        *,
        buyer_id: BuyerId,
        full_name: str,
        email: Email,
        document: Document,
        phone: Phone,
        password_hash: str,
        roles: frozenset[Role],
        now: datetime,
    ) -> "Buyer":
        normalized_name = " ".join(full_name.split())
        if len(normalized_name) < 3 or len(normalized_name.split()) < 2:
            raise ValidationError(
                "full name must contain given name and surname", field="full_name"
            )
        if len(normalized_name) > 120:
            raise ValidationError("full name is too long", field="full_name")
        if not password_hash:
            raise ValidationError("password hash is required", field="password")
        if not roles:
            raise ValidationError("at least one role is required", field="roles")
        return cls(
            id=buyer_id,
            full_name=normalized_name,
            email=email,
            document=document,
            phone=phone,
            password_hash=password_hash,
            roles=roles,
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def ensure_can_authenticate(self) -> None:
        if self.status is not AccountStatus.ACTIVE:
            raise AccountNotActiveError("account is not allowed to authenticate")

    def has_role(self, role: Role) -> bool:
        return role in self.roles
