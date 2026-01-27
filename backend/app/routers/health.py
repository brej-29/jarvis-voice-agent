from fastapi import APIRouter

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", summary="Health check", tags=["health"])
async def health() -> dict:
    """
    Lightweight health check endpoint for liveness probes and CI.
    """
    logger.debug("Health check requested")
    return {"status": "ok"}