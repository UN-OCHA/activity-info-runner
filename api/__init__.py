from .client import ActivityInfoHTTPClient
from .endpoints import ActivityInfoEndpoints

class ActivityInfoClient:
    def __init__(self, base_url: str, api_token: str | None = None):
        self._http = ActivityInfoHTTPClient(
            base_url=base_url,
            api_token=api_token,
        )
        self.api = ActivityInfoEndpoints(self._http)

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> "ActivityInfoClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()
