from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger
from app.routers import chat, health
from app.services.llamacpp_client import warmup_model as warmup_llamacpp_model

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

    @app.on_event("startup")
    async def _startup_llm_warmup() -> None:
        """
        Optionally warm up the LLM provider on startup.

        For LlamaCpp we trigger model download/initialization eagerly so that the
        first /chat request is faster. For Ollama there is nothing to warm up.
        """
        if settings.llm_provider == "llamacpp":
            logger.info("Warming up LlamaCpp TinyLlama model (provider=llamacpp)")
            await warmup_llamacpp_model()

    logger.info(
        "FastAPI application initialized (env=%s, provider=%s, model=%s, ollama_base=%s)",
        settings.app_env,
        settings.llm_provider,
        settings.debug_model_name,
        settings.ollama_base_url,
    )
    return app


app = create_app()