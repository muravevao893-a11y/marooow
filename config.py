from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    bot_username: str = Field(default="marooow_bot", alias="BOT_USERNAME")

    channel_id: int | str = Field(alias="CHANNEL_ID")
    discussion_chat_id: int | str = Field(alias="DISCUSSION_CHAT_ID")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    webhook_path: str = Field(default="/webhook", alias="WEBHOOK_PATH")
    webapp_host: str = Field(default="0.0.0.0", alias="WEBAPP_HOST")
    webapp_port: int = Field(default=8080, alias="WEBAPP_PORT")

    auto_drops_enabled: bool = Field(default=True, alias="AUTO_DROPS_ENABLED")
    auto_drop_title: str = Field(default="Кто хочет мишку?", alias="AUTO_DROP_TITLE")
    auto_drop_prize: str = Field(default="мишка", alias="AUTO_DROP_PRIZE")
    auto_drop_gift_id: str | None = Field(default=None, alias="AUTO_DROP_GIFT_ID")
    auto_drop_duration_seconds: int = Field(default=7200, alias="AUTO_DROP_DURATION_SECONDS")
    auto_drop_min_participants: int = Field(default=1, alias="AUTO_DROP_MIN_PARTICIPANTS")
    auto_drop_winners: int = Field(default=1, alias="AUTO_DROP_WINNERS")
    require_subscription: bool = Field(default=True, alias="REQUIRE_SUBSCRIPTION")
    gift_text: str = Field(default="забрал от &marooow", alias="GIFT_TEXT")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: str | list[int]) -> list[int]:
        if isinstance(value, list):
            return [int(v) for v in value]
        if not value:
            return []
        return [int(part.strip()) for part in str(value).split(",") if part.strip()]

    @field_validator("bot_username", mode="before")
    @classmethod
    def normalize_bot_username(cls, value: str) -> str:
        return str(value).strip().lstrip("@")

    @field_validator("webhook_url", mode="before")
    @classmethod
    def blank_webhook_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("channel_id", "discussion_chat_id", mode="before")
    @classmethod
    def parse_chat_id(cls, value: str | int) -> str | int:
        if isinstance(value, int):
            return value
        value = value.strip()
        if value.startswith("@"):
            return value
        try:
            return int(value)
        except ValueError:
            return value

    @field_validator("auto_drop_gift_id", mode="before")
    @classmethod
    def blank_gift_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @property
    def webhook_full_url(self) -> str | None:
        if not self.webhook_url:
            return None
        return self.webhook_url.rstrip("/") + self.webhook_path


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
