from __future__ import annotations
import io
import asyncio
import httpx
from PIL import Image as PILImage


class CoverCache:
    """Fetches and caches cover images (as decoded PIL images) keyed by URL, so
    each cover is downloaded once per session and tab switches are instant."""

    def __init__(self, http: httpx.AsyncClient, concurrency: int = 8) -> None:
        self._http = http
        self._cache: dict[str, PILImage.Image] = {}
        self._sem = asyncio.Semaphore(concurrency)

    def cached(self, url: str) -> PILImage.Image | None:
        return self._cache.get(url)

    async def get(self, url: str) -> PILImage.Image | None:
        if url in self._cache:
            return self._cache[url]
        async with self._sem:
            if url in self._cache:  # filled while waiting
                return self._cache[url]
            try:
                resp = await self._http.get(url)
                resp.raise_for_status()
                img = PILImage.open(io.BytesIO(resp.content))
                img.load()
            except (httpx.HTTPError, OSError):
                return None
        self._cache[url] = img
        return img

    async def preload(self, urls: list[str | None]) -> None:
        await asyncio.gather(*(self.get(u) for u in urls if u))
