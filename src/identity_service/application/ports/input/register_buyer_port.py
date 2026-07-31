from typing import Protocol

from identity_service.application.dto.commands import RegisterBuyerCommand
from identity_service.application.dto.outputs import BuyerOutput


class RegisterBuyerPort(Protocol):
    async def execute(self, command: RegisterBuyerCommand) -> BuyerOutput: ...
