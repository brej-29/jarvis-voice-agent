import logging
import os
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse


_DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_DEFAULT_TIMEOUT_S = 60
_VALID_ENVIRONMENTS = {"local", "dev", "prod"}
_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass
class Settings:
    """
    Application settings loaded from environment variables with sane defaults.

    This is intentionally lightweight (no external settings framework) and
    suitable for containerized or local development deployments.
    """

    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "local"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", _DEFAULT_OLLAMA_BASE_URL)
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "mistral"))
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

        # Validate and normalize base URL
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


settings = Settings()