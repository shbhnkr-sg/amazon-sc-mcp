"""
Amazon SP-API authentication via Login with Amazon (LWA) OAuth.
"""

import os
import time
import httpx


class SPAPIAuth:
    """Handles LWA access token refresh for SP-API calls."""

    def __init__(self):
        self.client_id = os.environ.get("SP_API_CLIENT_ID", "")
        self.client_secret = os.environ.get("SP_API_CLIENT_SECRET", "")
        self.refresh_token = os.environ.get("SP_API_REFRESH_TOKEN", "")
        self.token_url = os.environ.get(
            "SP_API_TOKEN_URL", "https://api.amazon.com/auth/o2/token"
        )
        self._access_token = ""
        self._token_expiry = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    async def get_access_token(self, client: httpx.AsyncClient | None = None) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        async def _refresh(c: httpx.AsyncClient) -> dict:
            resp = await c.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            resp.raise_for_status()
            return resp.json()

        if client:
            data = await _refresh(client)
        else:
            async with httpx.AsyncClient() as c:
                data = await _refresh(c)

        self._access_token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600) - 60
        return self._access_token

    async def auth_headers(self, client: httpx.AsyncClient | None = None) -> dict:
        """Return headers with Bearer token for SP-API calls."""
        if not self.configured:
            return {}
        token = await self.get_access_token(client)
        return {"x-amz-access-token": token}
