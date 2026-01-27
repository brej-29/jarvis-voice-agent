from pathlib import Path
import sys

import pytest

# Ensure backend package is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.chat import (  # noqa: E402
    ToolCall,
    ToolName,
    ToolRouterResult,
    ValidationError,
)


def test_tool_call_valid() -> None:
    call = ToolCall(
        name=ToolName.WEATHER,
        args={"city": "Berlin"},
        confidence=0.9,
    )
    assert call.name is ToolName.WEATHER
    assert call.args["city"] == "Berlin"
    assert 0.0 <= call.confidence <= 1.0


def test_tool_call_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        ToolCall(
            name=ToolName.GENERAL_QA,
            args={"answer": "Hi"},
            confidence=1.5,
        )


def test_tool_router_result_roundtrip() -> None:
    payload = {
        "tool_call": {
            "name": "SAVE_NOTE",
            "args": {"title": "Idea", "content": "Build Jarvis"},
            "confidence": 0.8,
        },
        "assistant_message": "I'll save that note.",
    }
    result = ToolRouterResult.model_validate(payload)
    assert result.tool_call.name is ToolName.SAVE_NOTE
    assert result.assistant_message == "I'll save that note."