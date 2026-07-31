from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError


class MongoReadinessProbe:
    def __init__(self, client: AsyncMongoClient[dict[str, Any]]) -> None:
        self._client = client

    async def check(self) -> bool:
        try:
            await self._client.admin.command("ping")
        except PyMongoError:
            return False
        return True
