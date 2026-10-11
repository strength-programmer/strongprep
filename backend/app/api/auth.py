"""Owner resolution.

demo: one fixed identity, loopback clients only, SQLite only (enforced at startup in main.py).
live: a valid Supabase-issued bearer token is REQUIRED. There is no fallback to the demo identity.
The owner is always derived from the verified token (`sub`); a client-supplied owner is never used.
"""
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, Request

from app.config import DEMO_OWNER_ID, Settings, get_settings

LOOPBACK = {"127.0.0.1", "::1", "localhost", "testclient"}


@lru_cache
def _jwks_client(url: str):
    return jwt.PyJWKClient(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json")


def verify_supabase_token(token: str, settings: Settings) -> str:
    if not settings.supabase_url:
        raise HTTPException(503, "Live mode is not configured: SUPABASE_URL is missing.")
    issuer = f"{settings.supabase_url.rstrip('/')}/auth/v1"
    try:
        if settings.supabase_jwt_secret:
            claims = jwt.decode(token, settings.supabase_jwt_secret, algorithms=["HS256"],
                                audience="authenticated", issuer=issuer, options={"require": ["exp", "sub"]})
        else:
            key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256", "ES256"],
                                audience="authenticated", issuer=issuer, options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired access token.", headers={"WWW-Authenticate": "Bearer"})
    except Exception:
        raise HTTPException(401, "Could not verify access token.", headers={"WWW-Authenticate": "Bearer"})
    return str(claims["sub"])


def _bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    if h.lower().startswith("bearer ") and h[7:].strip():
        return h[7:].strip()
    return None


def current_owner(request: Request, settings: Settings = Depends(get_settings)) -> str:
    if settings.is_demo:
        host = request.client.host if request.client else ""
        if host not in LOOPBACK:
            raise HTTPException(403, "Demo mode accepts local connections only.")
        return DEMO_OWNER_ID
    token = _bearer(request)
    if not token:
        raise HTTPException(401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    return verify_supabase_token(token, settings)


def optional_owner(request: Request, settings: Settings = Depends(get_settings)) -> str | None:
    """For public reads that also show the caller's own private rows. A bad token is an error, not anonymous."""
    if settings.is_demo:
        return current_owner(request, settings)
    if _bearer(request) is None:
        return None
    return current_owner(request, settings)


def soft_owner(request: Request, settings: Settings = Depends(get_settings)) -> str | None:
    """Like optional_owner, but a bad/expired token yields None instead of an error (used by /status)."""
    try:
        return optional_owner(request, settings)
    except HTTPException:
        return None
