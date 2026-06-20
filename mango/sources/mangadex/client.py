from __future__ import annotations
import asyncio
import httpx
from mango.util.rate_limiter import RateLimiter

USER_AGENT = "mango/0.1 (+https://github.com/local/mango)"


class MangaDexClient:
    def __init__(self, base_url: str = "https://api.mangadex.org",
                 max_retries: int = 4) -> None:
        self._rl = RateLimiter(rate=5.0, capacity=5)
        self._max_retries = max_retries
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
        )

    async def get_json(
        self, path: str, params: dict | list[tuple] | None = None,
        headers: dict | None = None,
    ) -> dict:
        attempt = 0
        while True:
            await self._rl.acquire()
            resp = await self._http.get(path, params=params, headers=headers)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self._max_retries:
                retry_after = float(resp.headers.get("Retry-After", 0) or 0)
                await asyncio.sleep(max(retry_after, 0.5 * (2 ** attempt)))
                attempt += 1
                continue
            resp.raise_for_status()
            return resp.json()

    @property
    def http(self) -> httpx.AsyncClient:
        return self._http

    async def aclose(self) -> None:
        await self._http.aclose()
