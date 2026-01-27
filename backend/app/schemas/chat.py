from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


MAX_CONTENT_LENGTH = 4000
MAX_MESSAGE_COUNT = 50


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    ts: datetime = Field(..., description="Timestamp in ISO8601 format")

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be empty or whitespace")
        return value


class ClientInfo(BaseModel):
    platform: Literal["android", "ios", "web"]
    app_version: str = Field(..., min_length=1, max_length=64)


class ChatSettings(BaseModel):
    response_style: Literal["concise", "normal", "detailed"] = "normal"


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    messages: List[ChatMessage]
    client: ClientInfo
    settings: ChatSettings = Field(default_factory=ChatSettings)

    @field_validator("messages")
    @classmethod
    def validate_messages_list(cls, value: List[ChatMessage]) -> List[ChatMessage]:
        if not value:
            raise ValueError("messages must contain at least one item")
        if len(value) > MAX_MESSAGE_COUNT:
            raise ValueError(
                f"messages must contain at most {MAX_MESSAGE_COUNT} items, "
                f"got {len(value)}"
            )
        return value

    @model_validator(mode="after")
    def validate_conversation(self) -> "ChatRequest":
        if not self.messages:
            # Already handled by field validator, but keep defensive.
            raise ValueError("messages must contain at least one item")

        last_role = self.messages[-1].role
        if last_role is not ChatRole.USER:
            raise ValueError(
                "last message in messages must have role 'user' for a chat request"
            )
        return self


class DebugInfo(BaseModel):
    model: str
    latency_ms: int = Field(..., ge=0)


class ToolName(str, Enum):
    WEATHER = "WEATHER"
    SET_REMINDER = "SET_REMINDER"
    SAVE_NOTE = "SAVE_NOTE"
    GENERAL_QA = "GENERAL_QA"


class ToolCall(BaseModel):
    """
    Structured representation of a tool call chosen by the model.

    The JSON contract exposed to the model is:

        {
          "name": "WEATHER"|"SET_REMINDER"|"SAVE_NOTE"|"GENERAL_QA",
          "args": { ... },
          "confidence": 0.0-1.0
        }
    """

    name: ToolName
    args: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)


class ToolRouterResult(BaseModel):
    """
    Container for the JSON object the model should return when routing tools.

        {
          "tool_call": ToolCall,
          "assistant_message": "optional natural language message"
        }
    """

    tool_call: ToolCall
    assistant_message: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    reply_text: str
    debug: DebugInfo
    errors: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of action objects for the client to execute, e.g. local notifications.",
    )
    tool_debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional debug information for tool routing, not for user display.",
    )

    @classmethod
    def friendly_error_response(
        cls,
        *,
        request: ChatRequest,
        reply_text: str,
        model: str,
        latency_ms: int,
        errors: List[str],
    ) -> "ChatResponse":
        """
        Helper for constructing a safe ChatResponse in error scenarios.
        """
        return cls(
            session_id=request.session_id,
            reply_text=reply_text,
            debug=DebugInfo(model=model, latency_ms=latency_ms),
            errors=errors,
        )


__all__ = [
    "ChatRole",
    "ChatMessage",
    "ClientInfo",
    "ChatSettings",
    "ChatRequest",
    "DebugInfo",
    "ChatResponse",
    "ToolName",
    "ToolCall",
    "ToolRouterResult",
    "ValidationError",
]