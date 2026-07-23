from identity_service.application.dto.commands import RegisterBuyerCommand
from identity_service.application.dto.outputs import BuyerOutput
from identity_service.application.ports.output.buyer_repository import BuyerRepository
from identity_service.application.ports.output.clock import Clock
from identity_service.application.ports.output.id_provider import IdProvider
from identity_service.application.ports.output.password_hasher import PasswordHasher
from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.role import Role
from identity_service.domain.services.password_policy import PasswordPolicy
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone


class RegisterBuyer:
    def __init__(
        self,
        repository: BuyerRepository,
        password_hasher: PasswordHasher,
        clock: Clock,
        id_provider: IdProvider,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_provider = id_provider

    async def execute(self, command: RegisterBuyerCommand) -> BuyerOutput:
        PasswordPolicy.ensure_strong(command.password)
        buyer = Buyer.register(
            buyer_id=BuyerId(self._id_provider.new_id()),
            full_name=command.full_name,
            email=Email(command.email),
            document=Document(command.document),
            phone=Phone(command.phone),
            password_hash=self._password_hasher.hash(command.password),
            roles=frozenset({Role.BUYER}),
            now=self._clock.now(),
        )
        await self._repository.insert(buyer)
        return BuyerOutput.from_entity(buyer)
