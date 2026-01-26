import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Logging filter that injects a request_id into each record."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        record.request_id = _request_id_ctx_var.get("-")
        return True


def set_request_id(request_id: str) -> None:
    _request_id_ctx_var.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx_var.get("-")


def configure_logging(level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    This function is idempotent: if handlers already exist on the root logger,
    it will not attach duplicate handlers.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Assume logging has already been configured by the process runner.
        return

    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name or "app")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a per-request ID for correlation in logs.

    The request ID is taken from the `X-Request-ID` header if present,
    otherwise a UUID4 value is generated.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        set_request_id(request_id)
        request.state.request_id = request_id
        logger = get_logger(__name__)
        logger.debug("Handling request %s %s", request.method, request.url.path)

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled exception while processing request")
            raise
        finally:
            # Reset context var to avoid leaking across requests in the same worker.
            set_request_id("-")

        response.headers["X-Request-ID"] = request_id
        return response