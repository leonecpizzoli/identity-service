import json
import logging
from datetime import UTC, datetime
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue

from identity_service.infrastructure.observability.correlation import correlation_id_var


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = correlation_id_var.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        event_fields = getattr(record, "event_fields", None)
        if isinstance(event_fields, dict):
            payload.update(event_fields)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> QueueListener:
    queue: SimpleQueue[logging.LogRecord] = SimpleQueue()
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonLogFormatter())
    listener = QueueListener(queue, stream_handler, respect_handler_level=True)
    listener.start()
    root_logger = logging.getLogger()
    root_logger.handlers = [QueueHandler(queue)]
    root_logger.setLevel(level.upper())
    for noisy_logger in ("uvicorn.access", "pymongo"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    return listener
