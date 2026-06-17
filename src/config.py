from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _get(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or str(v).strip() == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return str(v)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str

    api_base_url: str
    vk_oauth_token_url: str

    vk_client_id: str
    vk_client_secret: str
    # В вашем подходе токен запрашивается через Basic auth + grant_type=client_credentials
    # без redirect_uri и access_token.
    vk_redirect_uri: str = ""
    vk_access_token: str = ""


    # Behaviour
    request_timeout_seconds: int = 20


def load_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        api_base_url=os.getenv("API_BASE_URL", "https://apidev.live.vkvideo.ru"),
        vk_oauth_token_url=os.getenv("VK_OAUTH_TOKEN_URL", "https://api.live.vkvideo.ru/oauth/server/token"),
        vk_client_id=os.getenv("VK_CLIENT_ID"),
        vk_client_secret=os.getenv("VK_CLIENT_SECRET"),
        vk_redirect_uri=os.getenv("VK_REDIRECT_URI", ""),
        vk_access_token=os.getenv("VK_ACCESS_TOKEN", ""),

        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
    )
