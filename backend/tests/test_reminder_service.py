from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

# Ensure backend package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from app.services.reminder import (  # noqa: E402
    ReminderParseError,
    parse_natural_datetime,
)


def test_parse_natural_datetime_basic() -> None:
    now = datetime.now(timezone.utc)
    result = parse_natural_datetime("tomorrow at 3pm", base_time=now, timezone="UTC")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    assert result > now


def test_parse_natural_datetime_invalid() -> None:
    with pytest.raises(ReminderParseError):
        parse_natural_datetime("", timezone="UTC")