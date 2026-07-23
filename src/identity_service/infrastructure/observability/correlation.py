import re
from contextvars import ContextVar
from uuid import uuid4

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def resolve_correlation_id(candidate: str | None) -> str:
    if candidate and _CORRELATION_ID_PATTERN.fullmatch(candidate):
        return candidate
    return uuid4().hex


def current_correlation_id() -> str:
    return correlation_id_var.get() or "unknown"
