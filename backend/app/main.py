from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings


def check_startup(settings=None):
    s = settings or get_settings()
    if s.app_mode not in ("demo", "live"):
        raise RuntimeError("APP_MODE must be 'demo' or 'live'.")
    if s.is_demo and not s.database_url.startswith("sqlite"):
        raise RuntimeError("Demo mode may only use SQLite. Refusing to point the demo identity at a live database.")
    if not s.is_demo and not s.supabase_url:
        raise RuntimeError("APP_MODE=live requires SUPABASE_URL (and a database URL).")
    if not s.is_demo and not s.app_secret_key:
        raise RuntimeError("APP_MODE=live requires APP_SECRET_KEY (a Fernet key) to encrypt stored API keys.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_startup()
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="StrongPrep API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_origins, allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["X-Unknown-Distance-Count"])
    app.include_router(router)
    return app


app = create_app()
