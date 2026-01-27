import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.logging import get_logger, get_request_id
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    DebugInfo,
    ToolCall,
    ToolName,
    ToolRouterResult,
)
from app.services.ollama_client import (
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
)
from app.services.prompt_builder import build_system_prompt
from app.services.reminder import ReminderParseError, parse_natural_datetime
from app.services.weather import WeatherError, WeatherLookupError, get_weather_description

logger = get_logger(__name__)
router = APIRouter()

_ollama_client = OllamaClient()


def _build_tool_router_system_prompt() -> str:
    """
    Build a system prompt that instructs the model to perform tool routing.

    The model is required to return ONLY a JSON object matching ToolRouterResult.
    """
    base = build_system_prompt()
    contract = """
You MUST decide which tool to call for the user's latest message.

Available tools and when to use them:

- WEATHER: when the user asks about weather, forecast, temperature, or similar.
  - args: { "city": string (optional), "lat": float (optional), "lon": float (optional) }
- SET_REMINDER: when the user asks to remember something at a time or date.
  - args: { "title": string, "body": string, "datetime_text": string, "timezone": string (optional) }
- SAVE_NOTE: when the user wants to save a note, idea, or information for later.
  - args: { "title": string, "content": string }
- GENERAL_QA: for all other questions or small talk that do not require tools.
  - args: { "answer": string } where answer is the natural language reply you would give.

You MUST respond with ONLY valid JSON, no markdown, no extra text, with this shape:

{
  "tool_call": {
    "name": "WEATHER" | "SET_REMINDER" | "SAVE_NOTE" | "GENERAL_QA",
    "args": { ... },
    "confidence": 0.0-1.0
  },
  "assistant_message": "string | null"
}

- assistant_message is an optional natural-language reply that may be shown to the user.
- If you are not confident about a specific tool, prefer GENERAL_QA with a safe answer.
""".strip()

    if base:
        return base + "\n\n" + contract
    return contract


async def _call_router_model(messages: List[Dict[str, str]]) -> str:
    """
    Call Ollama to obtain a raw JSON string representing ToolRouterResult.
    """
    system_prompt = _build_tool_router_system_prompt()
    routed_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    routed_messages.extend(messages)
    return await _ollama_client.chat(messages=routed_messages)


def _parse_tool_router_result(raw: str) -> ToolRouterResult:
    """
    Parse the model's JSON output into ToolRouterResult.

    Raises ValueError if parsing fails.
    """
    data = json.loads(raw)
    return ToolRouterResult.model_validate(data)


async def _retry_fix_json(raw: str) -> Optional[ToolRouterResult]:
    """
    Ask the model once to fix invalid JSON output.

    Returns a ToolRouterResult on success, or None if it still fails.
    """
    logger.info("Retrying tool JSON parsing with fix prompt")
    fix_prompt = (
        "You previously returned invalid JSON for a tool routing decision. "
        "Here is your response:\n\n"
        f"{raw}\n\n"
        "Please return ONLY valid JSON that matches this schema:\n"
        "{"
        '"tool_call":{"name":"WEATHER"|"SET_REMINDER"|"SAVE_NOTE"|"GENERAL_QA","args":{},"confidence":0.0},'
        '"assistant_message":"string or null"'
        "}"
    )

    try:
        fixed_raw = await _ollama_client.chat(
            messages=[
                {"role": "system", "content": _build_tool_router_system_prompt()},
                {"role": "user", "content": fix_prompt},
            ]
        )
        return _parse_tool_router_result(fixed_raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("JSON fix attempt failed: %s", exc)
        return None


async def _handle_weather_tool(args: Dict[str, Any]) -> str:
    city = args.get("city")
    lat = args.get("lat")
    lon = args.get("lon")

    # Ensure numeric coordinates if provided
    try:
        lat_val = float(lat) if lat is not None else None
        lon_val = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        lat_val = None
        lon_val = None

    try:
        description = await get_weather_description(city=city, lat=lat_val, lon=lon_val)
        return description
    except WeatherLookupError as exc:
        logger.info("Weather lookup error: %s", exc)
        return str(exc)
    except WeatherError as exc:
        logger.warning("Weather service error: %s", exc)
        return (
            "I tried to look up the weather but the external weather service "
            "is currently unavailable."
        )


def _handle_set_reminder_tool(args: Dict[str, Any], actions: List[Dict[str, Any]]) -> str:
    title = str(args.get("title") or "Reminder")
    body = str(args.get("body") or title)
    datetime_text = str(args.get("datetime_text") or "")
    timezone = str(args.get("timezone") or "UTC")

    try:
        scheduled_dt = parse_natural_datetime(datetime_text, timezone=timezone)
    except ReminderParseError as exc:
        logger.info("Reminder parsing failed: %s", exc)
        return (
            "I could not understand the time for that reminder. "
            "Please specify a clearer date or time, for example 'tomorrow at 3 PM'."
        )

    scheduled_iso = scheduled_dt.isoformat()
    actions.append(
        {
            "type": "SCHEDULE_LOCAL_NOTIFICATION",
            "title": title,
            "body": body,
            "scheduled_for": scheduled_iso,
        }
    )
    return f"Okay, I will remind you: {title} at {scheduled_iso}."


def _handle_save_note_tool(args: Dict[str, Any], actions: List[Dict[str, Any]]) -> str:
    title = str(args.get("title") or "Note")
    content = str(args.get("content") or "")
    created_at = datetime.utcnow().isoformat()  # type: ignore[name-defined]

    actions.append(
        {
            "type": "SAVE_NOTE_LOCAL",
            "title": title,
            "content": content,
            "created_at": created_at,
        }
    )
    if content:
        return f"I've saved your note titled '{title}'."
    return "I've saved your note."


async def _handle_tool_call(
    tool_call: ToolCall,
    messages: List[Dict[str, str]],
    actions: List[Dict[str, Any]],
) -> str:
    """
    Execute the tool or fall back to a general QA answer.
    """
    name = tool_call.name
    args = tool_call.args or {}

    if name is ToolName.WEATHER:
        return await _handle_weather_tool(args)

    if name is ToolName.SET_REMINDER:
        return _handle_set_reminder_tool(args, actions)

    if name is ToolName.SAVE_NOTE:
        return _handle_save_note_tool(args, actions)

    # GENERAL_QA or anything unexpected: either use provided answer or call model again.
    answer = args.get("answer")
    if isinstance(answer, str) and answer.strip():
        return answer.strip()

    # Call the model again to generate a direct answer using the base system prompt.
    system_prompt = build_system_prompt()
    qa_messages: List[Dict[str, str]] = []
    if system_prompt:
        qa_messages.append({"role": "system", "content": system_prompt})
    qa_messages.extend(messages)

    try:
        return await _ollama_client.chat(messages=qa_messages)
    except OllamaClientError as exc:
        logger.error("GENERAL_QA model call failed: %s", exc)
        return (
            "I ran into an error while trying to answer that question. "
            "Please try again in a moment."
        )


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """
    Chat endpoint with tool routing.

    Flow:
    - Ask the local LLM to select a tool and respond with a strict JSON object.
    - Parse the JSON and execute tools for WEATHER, reminders, and notes.
    - Fall back to GENERAL_QA if JSON parsing or tool routing fails.
    """
    request_id = getattr(request.state, "request_id", get_request_id())
    logger.info("Handling /chat request for session %s", payload.session_id)

    start = time.perf_counter()
    errors: List[str] = []
    actions: List[Dict[str, Any]] = []
    tool_debug: Dict[str, Any] = {}

    # Convert conversation to simple role/content messages for the model.
    conversation_messages: List[Dict[str, str]] = [
        {"role": msg.role.value, "content": msg.content} for msg in payload.messages
    ]

    reply_text: str

    try:
        # Step 1: ask model to perform tool routing and return JSON only.
        raw = await _call_router_model(conversation_messages)
        tool_result = _parse_tool_router_result(raw)
    except (OllamaConnectionError, OllamaClientError) as exc:
        logger.warning(
            "Ollama error during tool routing for request_id=%s, session_id=%s: %s",
            request_id,
            payload.session_id,
            exc,
        )
        errors.append("ollama_connection_error")
        reply_text = (
            "I am currently unable to reach the local language model service. "
            "Please ensure Ollama is running and try again."
        )
    except Exception as exc:  # JSON parsing or validation error
        logger.warning(
            "Tool routing JSON parse failed for request_id=%s, session_id=%s: %s",
            request_id,
            payload.session_id,
            exc,
        )
        # Attempt one JSON-fix retry via the model.
        fixed_result = await _retry_fix_json(str(exc))
        if fixed_result is None:
            errors.append("tool_routing_json_error")
            # Fall back to a direct GENERAL_QA-style answer without tools.
            try:
                system_prompt = build_system_prompt()
                qa_messages: List[Dict[str, str]] = []
                if system_prompt:
                    qa_messages.append({"role": "system", "content": system_prompt})
                qa_messages.extend(conversation_messages)
                reply_text = await _ollama_client.chat(messages=qa_messages)
            except (OllamaConnectionError, OllamaClientError) as model_exc:
                logger.warning(
                    "Fallback GENERAL_QA model call failed for request_id=%s: %s",
                    request_id,
                    model_exc,
                )
                errors.append("ollama_connection_error")
                reply_text = (
                    "I am currently unable to generate a response because the local "
                    "language model service is unavailable."
                )
        else:
            tool_result = fixed_result  # type: ignore[unbound-local]
            tool_debug["json_fix_applied"] = True
            try:
                reply_text = await _handle_tool_call(
                    tool_result.tool_call, conversation_messages, actions
                )
                if tool_result.assistant_message:
                    # If the model provided a specific assistant message, prefer it.
                    reply_text = tool_result.assistant_message
            except Exception as tool_exc:  # noqa: BLE001
                logger.exception(
                    "Error executing tool after JSON fix for request_id=%s", request_id
                )
                errors.append("tool_execution_error")
                reply_text = (
                    "I had trouble executing the requested action. "
                    "Please try again or phrase your request differently."
                )
    else:
        # We have a valid ToolRouterResult from the first attempt.
        tool_debug["tool_call"] = tool_result.tool_call.model_dump()
        if tool_result.assistant_message:
            # Use the assistant_message directly when provided.
            reply_text = tool_result.assistant_message
        else:
            try:
                reply_text = await _handle_tool_call(
                    tool_result.tool_call, conversation_messages, actions
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Error executing tool for request_id=%s, session_id=%s",
                    request_id,
                    payload.session_id,
                )
                errors.append("tool_execution_error")
                reply_text = (
                    "I had trouble executing the requested action. "
                    "Please try again or phrase your request differently."
                )

    latency_ms = int((time.perf_counter() - start) * 1000)
    debug = DebugInfo(model=settings.ollama_model, latency_ms=latency_ms)
    response = ChatResponse(
        session_id=payload.session_id,
        reply_text=reply_text,
        debug=debug,
        errors=errors,
        actions=actions,
        tool_debug=tool_debug or None,
    )
    logger.info(
        "Completed /chat request for session %s in %sms with errors=%s",
        payload.session_id,
        latency_ms,
        errors,
    )
    return response