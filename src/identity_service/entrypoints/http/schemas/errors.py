from datetime import datetime

from pydantic import BaseModel, Field


class FieldErrorItem(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    timestamp: datetime
    path: str
    correlation_id: str
    field_errors: list[FieldErrorItem] = Field(default_factory=list)
