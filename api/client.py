# client.py
import asyncio

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import httpx
from typing import Optional, Dict, Any


# ---------- Exceptions ----------

class APIError(Exception):
    pass


class AuthenticationError(APIError):
    pass


class APITimeoutError(APIError):
    pass


# ---------- Client ----------

BASE_URL = "https://www.activityinfo.org/resources/"
DEFAULT_HEADERS = {
    "Accept": "application/json",
}


class ActivityInfoHTTPClient:
    def __init__(
            self,
            base_url: str,
            *,
            api_token: Optional[str] = None,
            timeout=httpx.Timeout(
                connect=10.0,
                read=60.0,
                write=10.0,
                pool=60.0
            ),
    ):
        headers = dict(DEFAULT_HEADERS)
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"

        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    async def request(
            self,
            method: str,
            path: str,
            *,
            params: Dict[str, Any] | None = None,
            json: Dict[str, Any] | None = None,
            retries: int = 3,
    ) -> Any:
        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                )

                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")

                if response.status_code >= 400:
                    raise APIError(
                        f"Error requesting {method} {response.url}: {response.status_code}: {response.text}"
                    )

                if not response.content:
                    return None

                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type.lower():
                    return None

                return response.json()

            except httpx.TimeoutException as exc:
                if attempt == retries - 1:
                    raise APITimeoutError("Request timed out") from exc
                await asyncio.sleep(2 ** attempt)
        return None

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ActivityInfoHTTPClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()
