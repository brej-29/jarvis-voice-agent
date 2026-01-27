from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

_CONTEXT_SNIPPET_CHARS = 800


def _find_context_dir() -> Path | None:
    """
    Locate the nearest `context/` directory by walking up from this file.

    This makes the prompt builder resilient to different working directories.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "context"
        if candidate.is_dir():
            return candidate
    logger.warning("context directory not found when building system prompt")
    return None


def _read_snippet(path: Path, limit: int = _CONTEXT_SNIPPET_CHARS) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        return text[:limit].strip()
    except FileNotFoundError:
        logger.warning("Context file not found for prompt building: %s", path)
        return ""
    except Exception:
        logger.exception("Failed to read context file for prompt building: %s", path)
        return ""


def build_system_prompt() -> str:
    """
    Build a concise system prompt for the local LLM.

    The prompt is constructed from small excerpts of GOAL.md and COMPONENTS.md
    to keep token usage low while grounding the assistant in the project's
    purpose and component structure.
    """
    context_dir = _find_context_dir()
    if context_dir is None:
        return (
            "You are Jarvis, a helpful local voice assistant running entirely on the "
            "user's machine. Keep responses concise and suitable for text-to-speech."
        )

    goal_snippet = _read_snippet(context_dir / "GOAL.md")
    components_snippet = _read_snippet(context_dir / "COMPONENTS.md")

    parts: list[str] = [
        "You are Jarvis, a local, voice-first assistant running via a FastAPI backend "
        "and a local Ollama LLM. You interact with a mobile Flutter client and your "
        "responses are spoken aloud via text-to-speech, so keep them clear and natural.",
    ]

    if goal_snippet:
        parts.append(
            "High-level product goals (excerpt):\n"
            f"{goal_snippet}"
        )

    if components_snippet:
        parts.append(
            "Key components and constraints (excerpt):\n"
            f"{components_snippet}"
        )

    parts.append(
        "General guidelines:\n"
        "- Respond concisely by default, suitable for real-time spoken output.\n"
        "- Avoid long monologues unless explicitly asked for more detail.\n"
        "- When clarifying or asking follow-up questions, keep them short and direct.\n"
        "- Assume you are assisting the user locally; do not reference remote services "
        "unless the user explicitly asks about them."
    )

    prompt = "\n\n".join(part.strip() for part in parts if part.strip())
    return prompt.strip()