from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str

    api_base_url: str
    request_timeout_seconds: float

    vk_client_id: str
    vk_client_secret: str
    vk_oauth_token_url: str


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        if default is None:
            raise RuntimeError(f"Missing environment variable: {name}")
        return default
    return value


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        api_base_url=_env("VKVIDEO_API_BASE_URL", "https://apidev.live.vkvideo.ru"),
        request_timeout_seconds=float(_env("REQUEST_TIMEOUT_SECONDS", "20")),
        vk_client_id=_env("VK_CLIENT_ID"),
        vk_client_secret=_env("VK_CLIENT_SECRET"),
        vk_oauth_token_url=_env(
            "VK_OAUTH_TOKEN_URL", "https://api.live.vkvideo.ru/oauth/server/token"
        ),
    )

