from pydantic import BaseModel, ConfigDict, Field


class RegisterBuyerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    document: str = Field(min_length=5, max_length=32)
    phone: str = Field(min_length=8, max_length=20)
    password: str = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)
