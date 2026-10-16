from dataclasses import asdict

from fastapi import APIRouter, Request

from app.connectors import get_connectors

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request) -> dict:
    scheduler = getattr(request.app.state, "scheduler", None)
    return {
        "status": "ok",
        "scheduler_running": bool(scheduler and scheduler.running),
    }


@router.get("/connectors")
async def connectors() -> list[dict]:
    """Each network's connection status. Checks credentials; never posts."""
    return [asdict(await c.check()) for c in get_connectors().values()]
