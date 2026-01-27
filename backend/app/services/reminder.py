from __future__ import annotations

from datetime import datetime
from typing import Optional

import dateparser

from app.core.logging import get_logger

logger = get_logger(__name__)


class ReminderParseError(Exception):
    """Raised when a natural-language datetime cannot be parsed."""


def parse_natural_datetime(
    text: str,
    *,
    base_time: Optional[datetime] = None,
    timezone: str = "UTC",
) -> datetime:
    """
    Parse a natural-language datetime expression into a timezone-aware datetime.

    This uses the `dateparser` library with a bias toward future dates.
    """
    if not text.strip():
        raise ReminderParseError("Empty datetime text")

    settings = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
        "TIMEZONE": timezone,
    }

    logger.debug("Parsing reminder datetime '%s' (timezone=%s)", text, timezone)
    parsed = dateparser.parse(text, settings=settings, languages=None, base=base_time)
    if parsed is None:
        raise ReminderParseError(f"Could not understand reminder time: '{text}'")

    return parsed