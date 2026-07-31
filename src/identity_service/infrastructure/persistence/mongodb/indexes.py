from typing import Any

from pymongo import ASCENDING, IndexModel
from pymongo.asynchronous.collection import AsyncCollection


async def ensure_buyer_indexes(collection: AsyncCollection[dict[str, Any]]) -> None:
    await collection.create_indexes(
        [
            IndexModel([("email", ASCENDING)], name="ux_buyers_email", unique=True),
            IndexModel([("document", ASCENDING)], name="ux_buyers_document", unique=True),
            IndexModel([("status", ASCENDING)], name="ix_buyers_status"),
            IndexModel([("created_at", ASCENDING)], name="ix_buyers_created_at"),
        ]
    )
