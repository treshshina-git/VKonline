from __future__ import annotations

import base64, requests
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from src.config import Settings, _env


@dataclass
class ApiToken:
    value: str
    expires_at: float  # unix timestamp


class ApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: Optional[ApiToken] = None

    async def get_vk_api_token(self) -> str:
        credentials = f"{_env("VK_CLIENT_ID")}:{_env("VK_CLIENT_SECRET")}"
        encoded = base64.b64encode(
        credentials.encode()
    ).decode()
        r = requests.post(
        {_env("TOKEN_VK_URL")},
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={"grant_type": "client_credentials"},
        timeout=30
        )

        now = time.time()
        if self._token and self._token.expires_at - 30 > now:
            return self._token.value

        credentials = f"{self.settings.vk_client_id}:{self.settings.vk_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        payload = {
            "grant_type": "client_credentials",
        }

        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.post(
                self.settings.vk_oauth_token_url,
                data=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()


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
        path = "/v1/catalog/online_categories"
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.get(f"{self.settings.api_base_url}{path}", headers=headers)
            resp.raise_for_status()
            data = resp.json()

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


        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.get(
                f"{self.settings.api_base_url}{path}",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected detail response format: {data}")
        return data