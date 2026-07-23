from datetime import datetime

from pydantic import BaseModel

from identity_service.application.dto.outputs import AccessTokenOutput, BuyerOutput


def _mask_document(document: str) -> str:
    if len(document) <= 3:
        return "***"
    return f"***{document[-3:]}"


class BuyerResponse(BaseModel):
    id: str
    full_name: str
    email: str
    document: str
    phone: str
    roles: list[str]
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_output(cls, output: BuyerOutput) -> "BuyerResponse":
        return cls(
            id=output.id,
            full_name=output.full_name,
            email=output.email,
            document=_mask_document(output.document),
            phone=output.phone,
            roles=list(output.roles),
            status=output.status,
            created_at=output.created_at,
            updated_at=output.updated_at,
        )


class UserSummaryResponse(BaseModel):
    id: str
    full_name: str
    email: str
    roles: list[str]

    @classmethod
    def from_output(cls, output: BuyerOutput) -> "UserSummaryResponse":
        return cls(
            id=output.id,
            full_name=output.full_name,
            email=output.email,
            roles=list(output.roles),
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserSummaryResponse

    @classmethod
    def from_output(cls, output: AccessTokenOutput) -> "TokenResponse":
        return cls(
            access_token=output.access_token,
            token_type=output.token_type,
            expires_in=output.expires_in,
            user=UserSummaryResponse.from_output(output.user),
        )


class HealthResponse(BaseModel):
    status: str
    service: str
