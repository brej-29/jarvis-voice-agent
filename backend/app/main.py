from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger
from app.routers import chat, health

configure_logging(settings.log_level)
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    """
    app = FastAPI(title="Jarvis Voice Agent API", version="0.1.0")

    # Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(chat.router)

    logger.info(
        "FastAPI application initialized (env=%s, model=%s, ollama_base=%s)",
        settings.app_env,
        settings.ollama_model,
        settings.ollama_base_url,
    )
    return app


app = create_app()