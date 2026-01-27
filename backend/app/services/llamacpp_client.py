from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LlamaCppClientError(Exception):
    """Base exception for LlamaCpp client related errors."""


class LlamaCppInitializationError(LlamaCppClientError):
    """Raised when the TinyLlama GGUF model cannot be downloaded or initialized."""


class LlamaCppInferenceError(LlamaCppClientError):
    """Raised when inference with the TinyLlama model fails."""


_model: Optional[Llama] = None
_model_lock: asyncio.Lock = asyncio.Lock()
_model_init_error: Optional[Exception] = None


def _blocking_init_model() -> Llama:
    """
    Download (if needed) and initialize the TinyLlama model.

    This runs in a worker thread so that it does not block the event loop.
    """
    repo_id = settings.llamacpp_model_repo
    filename = settings.llamacpp_model_file
    ctx_len = settings.llamacpp_context_length

    logger.info(
        "Downloading TinyLlama GGUF model from Hugging Face (repo=%s, file=%s)",
        repo_id,
        filename,
    )
    try:
        model_path = hf_hub_download(repo_id=repo_id, filename=filename)
        logger.info(
            "Initializing LlamaCpp model from %s (ctx=%s, max_tokens=%s)",
            model_path,
            ctx_len,
            settings.llamacpp_max_tokens,
        )
        model = Llama(
            model_path=model_path,
            n_ctx=ctx_len,
        )
        logger.info(
            "LlamaCpp TinyLlama model ready (provider=llamacpp, repo=%s, file=%s)",
            repo_id,
            filename,
        )
        return model
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to initialize LlamaCpp TinyLlama model")
        raise LlamaCppInitializationError(str(exc)) from exc


async def _ensure_model() -> Llama:
    """
    Ensure the global LlamaCpp model is initialized.

    Uses a lock to avoid duplicate initialization work across concurrent requests.
    """
    global _model, _model_init_error

    if _model is not None:
        return _model
    if _model_init_error is not None:
        raise _model_init_error  # type: ignore[misc]

    async with _model_lock:
        if _model is not None:
            return _model
        if _model_init_error is not None:
            raise _model_init_error  # type: ignore[misc]

        loop = asyncio.get_running_loop()
        try:
            _model = await loop.run_in_executor(None, _blocking_init_model)
            _model_init_error = None
            return _model
        except Exception as exc:  # noqa: BLE001
            _model_init_error = exc
            raise


async def warmup_model() -> None:
    """
    Optionally warm up the LlamaCpp model at application startup.

    For environments like Hugging Face Spaces this will trigger the GGUF download
    and model initialization so that the first /chat request is faster.
    """
    if settings.llm_provider != "llamacpp":
        return

    try:
        await _ensure_model()
    except Exception as exc:  # noqa: BLE001
        # We deliberately do not crash the app on warmup failure: the /chat route
        # will return a friendly degraded-demo message if initialization failed.
        logger.error("LlamaCpp warmup failed: %s", exc)


async def chat(messages: List[Dict[str, str]]) -> str:
    """
    Generate a reply using the TinyLlama GGUF model.

    This mirrors the Ollama client's interface: a list of role/content dicts and
    a single reply string. It builds a simple chat-style prompt and calls the
    model in a worker thread.
    """
    model = await _ensure_model()

    # Build a simple conversation prompt.
    parts: List[str] = []
    for msg in messages:
        role = (msg.get("role") or "user").lower()
        content = msg.get("content") or ""
        if not content:
            continue
        if role == "system":
            prefix = "System"
        elif role == "assistant":
            prefix = "Assistant"
        else:
            prefix = "User"
        parts.append(f"{prefix}: {content}")

    if not parts:
        raise LlamaCppInferenceError("No non-empty messages provided to LlamaCpp client")

    prompt = "\n".join(parts) + "\nAssistant:"

    max_tokens = settings.llamacpp_max_tokens

    def _blocking_chat() -> str:
        try:
            result: Dict[str, Any] = model(
                prompt,
                max_tokens=max_tokens,
                stop=["User:", "System:", "Assistant:"],
            )
        except Exception as exc:  # noqa: BLE001
            raise LlamaCppInferenceError(str(exc)) from exc

        try:
            choices = result.get("choices") or []
            if not choices:
                raise LlamaCppInferenceError("LlamaCpp returned no choices")
            text = choices[0].get("text", "")
        except Exception as exc:  # noqa: BLE001
            raise LlamaCppInferenceError(f"Invalid response from LlamaCpp: {exc}") from exc

        text = (text or "").strip()
        if not text:
            raise LlamaCppInferenceError("Empty response from LlamaCpp")
        return text

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _blocking_chat)
    except LlamaCppClientError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LlamaCppInferenceError(str(exc)) from exc