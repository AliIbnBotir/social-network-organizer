import asyncio
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app import auth
from app.connectors import get_connectors

router = APIRouter(prefix="/api")


@router.get("/health")
async def health(request: Request) -> dict:
    scheduler = getattr(request.app.state, "scheduler", None)
    return {
        "status": "ok",
        "scheduler_running": bool(scheduler and scheduler.running),
    }


@router.get("/auth")
async def auth_status(request: Request) -> dict:
    return {"auth_enabled": auth.auth_enabled(), "logged_in": auth.is_logged_in(request)}


class LoginIn(BaseModel):
    password: str


@router.post("/login")
async def login(data: LoginIn, response: Response) -> dict:
    if not auth.auth_enabled():
        return {"ok": True}
    if not auth.check_password(data.password):
        await asyncio.sleep(1)  # slows down password guessing
        raise HTTPException(status_code=401, detail="Wrong password.")
    auth.set_session_cookie(response)
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    auth.clear_session_cookie(response)
    return {"ok": True}


@router.get("/connectors", dependencies=[Depends(auth.require_login)])
async def connectors() -> list[dict]:
    """Each network's connection status. Checks credentials; never posts."""
    return [asdict(await c.check()) for c in get_connectors().values()]
