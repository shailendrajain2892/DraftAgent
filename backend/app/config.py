"""Application settings, loaded from environment variables (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OAuth / Google
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # Session
    session_secret: str = "dev-insecure-secret-change-me"
    session_cookie_name: str = "draftagent_session"
    cookie_secure: bool = False  # set True in AWS (HTTPS)

    # CORS (only needed if UI served from a different origin)
    frontend_origin: str = ""

    # OpenAI (used by the agent; backend just passes config through)
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    # Style store
    style_store_dir: str = "./.data/style_store"
    seed_days: int = 30
    seed_max_pairs: int = 300
    cold_start_min_pairs: int = 30
    style_mode: str = "retrieval"  # or "summary_only"

    # Agent
    max_agent_steps: int = 6
    checkpointer_db: str = "./.data/checkpoints.sqlite"

    # Gmail client behaviour
    gmail_max_concurrency: int = 5
    gmail_max_retries: int = 3

    @property
    def gmail_scopes(self) -> list[str]:
        return [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
