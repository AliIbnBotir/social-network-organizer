"""Single-password login for the dashboard.

There is one user (you), so there are no accounts: logging in with
DASHBOARD_PASSWORD sets a signed cookie. The signing key is derived from the
password, so changing the password logs every browser out.
"""

import hashlib
import hmac
import time

from fastapi import HTTPException, Request, Response

from app.config import get_settings

COOKIE_NAME = "sno_session"
SESSION_SECONDS = 30 * 24 * 3600


def auth_enabled() -> bool:
    return bool(get_settings().dashboard_password)


def _key() -> bytes:
    return hashlib.sha256(f"sno-session:{get_settings().dashboard_password}".encode()).digest()


def _sign(expires: int) -> str:
    return hmac.new(_key(), str(expires).encode(), hashlib.sha256).hexdigest()


def check_password(password: str) -> bool:
    return hmac.compare_digest(password.encode(), get_settings().dashboard_password.encode())


def set_session_cookie(response: Response) -> None:
    expires = int(time.time()) + SESSION_SECONDS
    response.set_cookie(
        COOKIE_NAME,
        f"{expires}.{_sign(expires)}",
        max_age=SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=get_settings().cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def is_logged_in(request: Request) -> bool:
    if not auth_enabled():
        return True
    expires, _, signature = request.cookies.get(COOKIE_NAME, "").partition(".")
    if not expires.isdigit() or int(expires) < time.time():
        return False
    return hmac.compare_digest(signature, _sign(int(expires)))


def require_login(request: Request) -> None:
    """Route dependency: 401 unless logged in (or no password is set)."""
    if not is_logged_in(request):
        raise HTTPException(status_code=401, detail="Log in first.")
