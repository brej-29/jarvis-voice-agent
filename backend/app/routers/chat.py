import time
from typing import List

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.logging import get_logger, get_request_id
from app.schemas.chat import ChatRequest, ChatResponse, DebugInfo
from app.services.ollama_client import (
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
)
from app.services.prompt_builder import build_system_prompt

logger = get_logger(__name__)
router = APIRouter()

_ollama_client = OllamaClient()


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """
    Chat endpoint that forwards the conversation to a local Ollama instance.

    - Validates the incoming request via Pydantic.
    - Builds a concise system prompt from context files.
    - Calls Ollama /api/chat through the OllamaClient.
    - Measures latency and returns a structured ChatResponse.
    - Handles errors gracefully, never leaking stack traces to the client.
    """
    request_id = getattr(request.state, "request_id", get_request_id())
    logger.info("Handling /chat request for session %s", payload.session_id)

    start = time.perf_counter()
    errors: List[str] = []

    try:
        system_prompt = build_system_prompt()
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for msg in payload.messages:
            messages.append({"role": msg.role.value, "content": msg.content})

        reply_text = await _ollama_client.chat(messages=messages)

    except OllamaConnectionError as exc:
        logger.warning(
            "Ollama connection error for request_id=%s, session_id=%s: %s",
            request_id,
            payload.session_id,
            exc,
        )
        errors.append("ollama_connection_error")
        reply_text = (
            "I am currently unable to reach the local language model service. "
            "Please ensure Ollama is running and try again."
        )
    except OllamaClientError as exc:
        logger.error(
            "Ollama client error for request_id=%s, session_id=%s: %s",
            request_id,
            payload.session_id,
            exc,
        )
        errors.append("ollama_client_error")
        reply_text = (
            "I ran into an internal error while generating a reply. "
            "Please try again in a moment."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error while handling /chat for request_id=%s, session_id=%s",
            request_id,
            payload.session_id,
        )
        errors.append("unexpected_server_error")
        reply_text = (
            "Something went wrong while handling your request. "
            "Please try again later."
        )

    latency_ms = int((time.perf_counter() - start) * 1000)
    debug = DebugInfo(model=settings.ollama_model, latency_ms=latency_ms)
    response = ChatResponse(
        session_id=payload.session_id,
        reply_text=reply_text,
        debug=debug,
        errors=errors,
    )
    logger.info(
        "Completed /chat request for session %s in %sms with errors=%s",
        payload.session_id,
        latency_ms,
        errors,
    )
    return response