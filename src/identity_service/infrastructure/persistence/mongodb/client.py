from typing import Any

from pymongo import AsyncMongoClient

from identity_service.infrastructure.settings.config import MongoSettings


def create_mongo_client(settings: MongoSettings) -> AsyncMongoClient[dict[str, Any]]:
    return AsyncMongoClient(
        settings.uri,
        minPoolSize=settings.min_pool_size,
        maxPoolSize=settings.max_pool_size,
        serverSelectionTimeoutMS=settings.server_selection_timeout_ms,
        timeoutMS=settings.operation_timeout_ms,
        tz_aware=True,
    )
