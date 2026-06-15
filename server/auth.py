"""
Token 鉴权中间件

@author buchi
@since 2026-06-15
"""
import os
import secrets
from pathlib import Path

from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

TOKEN_FILE = Path.home() / ".wchat_token"
_bearer_scheme = HTTPBearer()


def generate_token() -> str:
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)
    return token


def load_or_create_token() -> str:
    env_token = os.environ.get("WCHAT_TOKEN")
    if env_token:
        return env_token
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return generate_token()


_server_token: str = ""


def init_token() -> str:
    global _server_token
    _server_token = load_or_create_token()
    return _server_token


def verify_token(token: str) -> bool:
    return secrets.compare_digest(token, _server_token)


class TokenAuthMiddleware(BaseHTTPMiddleware):
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # WebSocket 鉴权走 query param
        if request.url.path.startswith("/ws/"):
            ws_token = request.query_params.get("token", "")
            if not verify_token(ws_token):
                raise HTTPException(status_code=403, detail="Invalid token")
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing authorization header")

        token = auth_header[7:]
        if not verify_token(token):
            raise HTTPException(status_code=403, detail="Invalid token")

        return await call_next(request)
