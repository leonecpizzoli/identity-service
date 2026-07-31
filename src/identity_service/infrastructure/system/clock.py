from datetime import UTC, datetime


class UtcClock:
    def now(self) -> datetime:
        current = datetime.now(UTC)
        return current.replace(microsecond=(current.microsecond // 1000) * 1000)
