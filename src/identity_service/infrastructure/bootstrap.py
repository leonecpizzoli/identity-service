from identity_service.application.ports.output.buyer_repository import BuyerRepository
from identity_service.application.ports.output.clock import Clock
from identity_service.application.ports.output.id_provider import IdProvider
from identity_service.application.ports.output.password_hasher import PasswordHasher
from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.role import Role
from identity_service.domain.exceptions.errors import (
    DocumentAlreadyRegisteredError,
    EmailAlreadyRegisteredError,
    RegistrationConflictError,
)
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone
from identity_service.infrastructure.settings.config import BootstrapSettings


async def ensure_bootstrap_admin(
    settings: BootstrapSettings,
    repository: BuyerRepository,
    password_hasher: PasswordHasher,
    clock: Clock,
    id_provider: IdProvider,
) -> None:
    if not settings.admin_email or not settings.admin_password:
        return
    email = Email(settings.admin_email)
    if await repository.find_by_email(email) is not None:
        return
    admin = Buyer.register(
        buyer_id=BuyerId(id_provider.new_id()),
        full_name=settings.admin_full_name,
        email=email,
        document=Document(settings.admin_document),
        phone=Phone(settings.admin_phone),
        password_hash=password_hasher.hash(settings.admin_password),
        roles=frozenset({Role.ADMIN}),
        now=clock.now(),
    )
    try:
        await repository.insert(admin)
    except (
        EmailAlreadyRegisteredError,
        DocumentAlreadyRegisteredError,
        RegistrationConflictError,
    ):
        return
