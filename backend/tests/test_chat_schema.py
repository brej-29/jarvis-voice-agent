from pathlib import Path
import sys

import pytest

# Ensure the backend app package is importable whether tests are run from the
# repo root or from the backend directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
  sys.path.insert(0, str(BACKEND_DIR))

from app.schemas.chat import (  # noqa: E402  (import after sys.path modification)
    ChatMessage,
    ChatRequest,
    ChatRole,
    ChatSettings,
    ClientInfo,
    ValidationError,
)


def test_chat_message_valid() -> None:
    msg = ChatMessage(
        role=ChatRole.USER,
        content="Hello, Jarvis",
        ts="2024-01-01T00:00:00Z",
    )
    assert msg.role is ChatRole.USER
    assert msg.content == "Hello, Jarvis"


def test_chat_message_invalid_role() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(
            role="invalid",  # type: ignore[arg-type]
            content="Hello",
            ts="2024-01-01T00:00:00Z",
        )


def test_chat_message_content_length_limit() -> None:
    long_text = "x" * 5001
    with pytest.raises(ValidationError):
        ChatMessage(
            role=ChatRole.USER,
            content=long_text,
            ts="2024-01-01T00:00:00Z",
        )


def test_chat_request_requires_messages() -> None:
    client_info = ClientInfo(platform="android", app_version="0.1.0")
    settings = ChatSettings()

    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-1",
            messages=[],
            client=client_info,
            settings=settings,
        )


def test_chat_request_last_message_must_be_user() -> None:
    client_info = ClientInfo(platform="android", app_version="0.1.0")
    settings = ChatSettings()

    user_msg = ChatMessage(
        role=ChatRole.USER,
        content="Hi",
        ts="2024-01-01T00:00:00Z",
    )
    assistant_msg = ChatMessage(
        role=ChatRole.ASSISTANT,
        content="Hello",
        ts="2024-01-01T00:00:01Z",
    )

    # Valid: last message is user
    ChatRequest(
        session_id="session-1",
        messages=[assistant_msg, user_msg],
        client=client_info,
        settings=settings,
    )

    # Invalid: last message is assistant
    with pytest.raises(ValidationError):
        ChatRequest(
            session_id="session-1",
            messages=[user_msg, assistant_msg],
            client=client_info,
            settings=settings,
        )