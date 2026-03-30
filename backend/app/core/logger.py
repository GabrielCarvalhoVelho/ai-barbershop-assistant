import logging

from app.core.context import get_request_id

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | rid=%(request_id)s | %(message)s"


class RequestIDFilter(logging.Filter):
    """Injeta request_id do contextvars em todo log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logger():
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.addFilter(RequestIDFilter())
        root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
