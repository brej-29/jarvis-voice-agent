import logging
import os
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse


_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT_S = 60
_DEFAULT_LLM_PROVIDER = "ollama"
_DEFAULT_LLAMACPP_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
_DEFAULT_LLAMACPP_MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
_DEFAULT_LLAMACPP_CONTEXT_LENGTH = 2048
_DEFAULT_LLAMACPP_MAX_TOKENS = 256

_VALID_ENVIRONMENTS = {"local", "dev", "prod"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_LLM_PROVIDERS = {"ollama", "llamacpp"}


@dataclass
class Settings:
    """
    Application settings loaded from environment variables with sane defaults.

    This is intentionally lightweight (no external settings framework) and
    suitable for containerized or local development deployments.
    """

    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # LLM provider selection
    # - "ollama"   -> local Ollama instance (default, local-first)
    # - "llamacpp" -> CPU-only TinyLlama model (for HF Spaces / demos)
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", _DEFAULT_LLM_PROVIDER)
    )

    # Ollama configuration (used when llm_provider == "ollama")
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "mistral"))

    # LlamaCpp configuration (used when llm_provider == "llamacpp")
    llamacpp_model_repo: str = field(
        default_factory=lambda: os.getenv("LLAMACPP_MODEL_REPO", _DEFAULT_LLAMACPP_REPO)
    )
    llamacpp_model_file: str = field(
        default_factory=lambda: os.getenv(
            "LLAMACPP_MODEL_FILE", _DEFAULT_LLAMACPP_MODEL_FILE
        )
    )
    llamacpp_context_length: int = field(
        default_factory=lambda: int(
            os.getenv("LLAMACPP_CONTEXT_LENGTH", str(_DEFAULT_LLAMACPP_CONTEXT_LENGTH))
        )
    )
    llamacpp_max_tokens: int = field(
        default_factory=lambda: int(
            os.getenv("LLAMACPP_MAX_TOKENS", str(_DEFAULT_LLAMACPP_MAX_TOKENS))
        )
    )

    request_timeout_s: int = field(
        default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_S", str(_DEFAULT_TIMEOUT_S)))
    )
    cors_allow_origins: List[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://10.0.2.2:8000,http://localhost:8000",
        ).split(",")
    )

    def __post_init__(self) -> None:
        logger = logging.getLogger(__name__)

        # Normalize and validate environment
        original_env = self.app_env
        self.app_env = (self.app_env or "local").lower()
        if self.app_env not in _VALID_ENVIRONMENTS:
            logger.warning(
                "Invalid APP_ENV '%s' provided; defaulting to 'local'", original_env
            )
            self.app_env = "local"

        # Normalize and validate log level
        original_log_level = self.log_level
        self.log_level = (self.log_level or "INFO").upper()
        if self.log_level not in _VALID_LOG_LEVELS:
            logger.warning(
                "Invalid LOG_LEVEL '%s' provided; defaulting to 'INFO'", original_log_level
            )
            self.log_level = "INFO"

        # Normalize and validate LLM provider
        original_provider = self.llm_provider
        self.llm_provider = (self.llm_provider or _DEFAULT_LLM_PROVIDER).lower()
        if self.llm_provider not in _VALID_LLM_PROVIDERS:
            logger.warning(
                "Invalid LLM_PROVIDER '%s' provided; defaulting to '%s'",
                original_provider,
                _DEFAULT_LLM_PROVIDER,
            )
            self.llm_provider = _DEFAULT_LLM_PROVIDER

        # Validate timeout
        try:
            timeout_value = int(self.request_timeout_s)
            if timeout_value <= 0:
                raise ValueError
            self.request_timeout_s = timeout_value
        except (TypeError, ValueError):
            logger.warning(
                "Invalid REQUEST_TIMEOUT_S '%s'; defaulting to %s seconds",
                self.request_timeout_s,
                _DEFAULT_TIMEOUT_S,
            )
            self.request_timeout_s = _DEFAULT_TIMEOUT_S

        # Validate and normalize base URL (for Ollama)
        parsed_url = urlparse(self.ollama_base_url or "")
        if not parsed_url.scheme or not parsed_url.netloc:
            logger.warning(
                "Invalid OLLAMA_BASE_URL '%s'; defaulting to '%s'",
                self.ollama_base_url,
                _DEFAULT_OLLAMA_BASE_URL,
            )
            self.ollama_base_url = _DEFAULT_OLLAMA_BASE_URL
        else:
            # Normalize trailing slashes
            self.ollama_base_url = self.ollama_base_url.rstrip("/")

        # Validate LlamaCpp numeric settings
        try:
            ctx = int(self.llamacpp_context_length)
            if ctx <= 0:
                raise ValueError
            self.llamacpp_context_length = ctx
        except (TypeError, ValueError):
            logger.warning(
                "Invalid LLAMACPP_CONTEXT_LENGTH '%s'; defaulting to %s",
                self.llamacpp_context_length,
                _DEFAULT_LLAMACPP_CONTEXT_LENGTH,
            )
            self.llamacpp_context_length = _DEFAULT_LLAMACPP_CONTEXT_LENGTH

        try:
            max_tokens = int(self.llamacpp_max_tokens)
            if max_tokens <= 0:
                raise ValueError
            self.llamacpp_max_tokens = max_tokens
        except (TypeError, ValueError):
            logger.warning(
                "Invalid LLAMACPP_MAX_TOKENS '%s'; defaulting to %s",
                self.llamacpp_max_tokens,
                _DEFAULT_LLAMACPP_MAX_TOKENS,
            )
            self.llamacpp_max_tokens = _DEFAULT_LLAMACPP_MAX_TOKENS

        # Normalize and clean CORS origins
        cleaned_origins: List[str] = []
        for origin in self.cors_allow_origins:
            origin = origin.strip()
            if origin:
                cleaned_origins.append(origin)
        if not cleaned_origins:
            logger.warning(
                "No valid CORS_ALLOW_ORIGINS provided; defaulting to '*' for local use only"
            )
            cleaned_origins = ["*"]
        self.cors_allow_origins = cleaned_origins

    @property
    def log_level_int(self) -> int:
        """Return the logging module constant for the configured log level."""
        return getattr(logging, self.log_level, logging.INFO)

    @property
    def debug_model_name(self) -> str:
        """
        Return a human-readable model identifier for debug responses.

        For Ollama we use the configured model name.
        For LlamaCpp we surface the GGUF file name.
        """
        if self.llm_provider == "llamacpp":
            return self.llamacpp_model_file
        return self.ollama_model


settings = Settings()