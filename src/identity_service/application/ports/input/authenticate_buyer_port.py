from typing import Protocol

from identity_service.application.dto.commands import LoginCommand
from identity_service.application.dto.outputs import AccessTokenOutput


class AuthenticateBuyerPort(Protocol):
    async def execute(self, command: LoginCommand) -> AccessTokenOutput: ...
