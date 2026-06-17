from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

from src.config import Settings


@dataclass
class ApiToken:
    value: str
    expires_at: float  # unix timestamp


class ApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: Optional[ApiToken] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout_seconds)
        return aiohttp.ClientSession(timeout=timeout)

    async def get_vk_api_token(self) -> str:
        """Получает токен для доступа к API.

        ВАЖНО: вам нужно подставить параметры в запрос к VK_OAUTH_TOKEN_URL так,
        как ожидает ваш endpoint.
        """

        now = time.time()
        if self._token and self._token.expires_at - 30 > now:
            return self._token.value

        import base64

        credentials = f"{self.settings.vk_client_id}:{self.settings.vk_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        payload = {
            "grant_type": "client_credentials",
        }

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with await self._get_session() as session:
            async with session.post(
                self.settings.vk_oauth_token_url,
                data=payload,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()


        token_value = (
            data.get("access_token")
            or data.get("token")
            or data.get("result")
        )
        if not token_value:
            raise RuntimeError(f"Unexpected token response format: {data}")

        # expires_in возможен в секундах
        expires_in = data.get("expires_in") or data.get("expiresIn") or 3600
        try:
            expires_in = int(expires_in)
        except Exception:
            expires_in = 3600

        self._token = ApiToken(value=str(token_value), expires_at=now + expires_in)
        return self._token.value

    async def fetch_active_positions_list(self) -> List[Dict[str, Any]]:
        """GET: активные категории.

        По вашей схеме:
        GET {API_BASE_URL}/v1/catalog/active_channels

        Ответ:
        {
          "data": {"categories": [ {"id": ..., "title": ...}, ... ]}
        }
        """
        token = await self.get_vk_api_token()
        path = "/v1/catalog/active_channels"
        headers = {"Authorization": f"Bearer {token}"}

        async with await self._get_session() as session:
            async with session.get(f"{self.settings.api_base_url}{path}", headers=headers) as resp:
                resp.raise_for_status()
                data = await resp.json()

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected list response format: {data}")

        categories = data.get("data", {}).get("categories")
        if not isinstance(categories, list):
            raise RuntimeError(f"Unexpected list response format (categories): {data}")

        return categories

    async def fetch_position_detail(self, position_id: str) -> Dict[str, Any]:
        """GET: каналы/элементы для выбранной категории.

        По вашей схеме:
        GET {API_BASE_URL}/v1/catalog/online_channels?channel_id=<category_id>

        Ответ:
        {
          "data": {"channels": [ {"channel": {...}, "stream": {...}, ...}, ... ]}
        }
        """
        token = await self.get_vk_api_token()

        path = "/v1/catalog/online_channels"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            # Параметры из документации/ответа API
            "limit": 200,
            "category_id": position_id,
            # Можно дополнительно включать фильтры при необходимости:
            # "category_type": "irl",
            # "has_vk_video": False,
            # "all_streams": False,
            # "offset": 0,
        }


        async with await self._get_session() as session:
            async with session.get(
                f"{self.settings.api_base_url}{path}",
                headers=headers,
                params=params,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected detail response format: {data}")
        return data



