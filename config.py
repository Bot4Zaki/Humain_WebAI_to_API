"""
Central configuration loaded from environment / .env file.

No secrets, no credentials. Only operational parameters.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Server ────────────────────────────────────────────────
    host: str = "127.0.0.1"
    port: int = 8100

    # ── Browser ───────────────────────────────────────────────
    browser_profile_dir: Path = Path("./browser_data")
    humain_chat_url: str = "https://chat.humain.ai"

    # ── Behaviour ─────────────────────────────────────────────
    response_timeout: int = 120  # seconds to wait for a reply
    rate_limit_per_minute: int = 10

    # ── Logging ───────────────────────────────────────────────
    log_level: str = "INFO"


settings = Settings()  # singleton
