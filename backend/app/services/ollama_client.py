from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClientError(Exception):
    """Base exception for Ollama client related errors."""


class OllamaConnectionError(OllamaClientError):
    """Raised when the client cannot reach the Ollama service."""


class OllamaResponseError(OllamaClientError):
    """Raised when Ollama returns an unexpected or invalid response."""


class OllamaClient:
    """
    Thin async client wrapper around the Ollama /api/chat endpoint.

    The interface is intentionally minimal: it accepts a list of messages and
    returns a single reply string.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_s: int | None = None,
        max_retries: int = 2,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout_s = timeout_s or settings.request_timeout_s
        self.max_retries = max_retries

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Send a chat request to Ollama and return the assistant's reply text.

        :param messages: List of dicts with at least {"role": ..., "content": ...}.
        :raises OllamaClientError: If the request fails or the response is invalid.
        """
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        last_exc: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return self._extract_reply(data)
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    "Network error talking to Ollama (attempt %s/%s): %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                continue
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error from Ollama: status=%s, body=%s",
                    exc.response.status_code,
                    exc.response.text,
                )
                raise OllamaResponseError(
                    f"Ollama HTTP error {exc.response.status_code}"
                ) from exc
            except (ValueError, KeyError, TypeError) as exc:
                logger.error("Invalid response from Ollama: %s", exc)
                raise OllamaResponseError("Invalid response structure from Ollama") from exc

        raise OllamaConnectionError(
            f"Failed to connect to Ollama at {url} after {self.max_retries} attempts"
        ) from last_exc

    @staticmethod
    def _extract_reply(data: Dict[str, Any]) -> str:
        """
        Extract the assistant's reply text from the Ollama response payload.

        Expected shape (as of Ollama chat API):

            {
              "model": "...",
              "created_at": "...",
              "message": {
                "role": "assistant",
                "content": "..."
              },
              ...
            }
        """
        try:
            message = data["message"]
            content = message["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaResponseError("Missing 'message.content' in Ollama response") from exc

        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Empty content returned from Ollama")
        return content.strip()