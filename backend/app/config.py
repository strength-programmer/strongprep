from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEMO_OWNER_ID = "demo-athlete"
CALCULATION_VERSION = "gap-rules-1.0"
RECENT_RECORD_DAYS = 365
MIN_PERCENTILE_COHORT = 20


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: str = "demo"  # demo | live
    database_url: str = "sqlite:///./strongprep-demo.db"
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    ai_provider: str = "mock"  # mock | claude
    anthropic_api_key: str = ""
    claude_model: str = ""

    # Any OpenAI-compatible chat endpoint (e.g. Qwen via DashScope, or a proxy). AI_PROVIDER=openai_compatible
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # Fernet key used to encrypt API keys entered in the app. Required in live mode; demo auto-creates a local file.
    app_secret_key: str = ""

    tavily_api_key: str = ""
    firecrawl_api_key: str = ""

    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

