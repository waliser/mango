from __future__ import annotations
import time
from dataclasses import replace
from mango.models import Manga, Chapter, Page
from mango.sources.base import Source
from mango.sources.mangadex.client import MangaDexClient
from mango.sources.mangadex import auth
from mango.sources.mangadex.auth import AuthSession
from mango.storage import tokens

UPLOADS = "https://uploads.mangadex.org"


def _pick(d: dict, lang: str = "en") -> str:
    if not d:
        return ""
    return d.get(lang) or next(iter(d.values()), "")


class MangaDexSource(Source):
    id = "mangadex"
    name = "MangaDex"
    supports_auth = True

    def __init__(self) -> None:
        self._client = MangaDexClient()
        self._session: AuthSession | None = tokens.load_session()

    async def search(self, query: str, *, limit: int = 20, offset: int = 0) -> list[Manga]:
        data = await self._client.get_json("/manga", params=[
            ("title", query), ("limit", limit), ("offset", offset),
            ("includes[]", "cover_art"),
            ("contentRating[]", "safe"), ("contentRating[]", "suggestive"),
            ("contentRating[]", "erotica"),
        ])
        manga = [self._to_manga(item) for item in data.get("data", [])]
        return await self._attach_stats(manga)

    async def _attach_stats(self, manga: list[Manga]) -> list[Manga]:
        """Fill rating/follows from the statistics endpoint (one extra call)."""
        if not manga:
            return manga
        params = [("manga[]", m.id) for m in manga]
        try:
            data = await self._client.get_json("/statistics/manga", params=params)
        except Exception:
            return manga  # stats are non-essential; show results without them
        stats = data.get("statistics", {}) or {}
        out: list[Manga] = []
        for m in manga:
            s = stats.get(m.id, {})
            rating = (s.get("rating") or {}).get("bayesian")
            out.append(replace(m, rating=rating, follows=s.get("follows")))
        return out

    async def get_chapters(self, manga_id: str, *, language: str = "en") -> list[Chapter]:
        out: list[Chapter] = []
        offset = 0
        while True:
            data = await self._client.get_json(f"/manga/{manga_id}/feed", params=[
                ("translatedLanguage[]", language),
                ("order[chapter]", "asc"),
                ("limit", 100), ("offset", offset),
                ("includes[]", "scanlation_group"),
            ])
            items = data.get("data", [])
            for it in items:
                attrs = it.get("attributes", {})
                if attrs.get("externalUrl"):  # external-only chapters can't be read inline
                    continue
                group = ""
                for rel in it.get("relationships", []):
                    if rel.get("type") == "scanlation_group":
                        group = (rel.get("attributes") or {}).get("name", "") or ""
                out.append(Chapter(
                    id=it["id"],
                    number=attrs.get("chapter") or "0",
                    title=attrs.get("title") or "",
                    language=attrs.get("translatedLanguage") or language,
                    group=group,
                ))
            total = data.get("total", 0)
            offset += len(items)
            if offset >= total or not items:
                break
        return out

    async def get_pages(self, chapter_id: str, *, data_saver: bool = False) -> list[Page]:
        data = await self._client.get_json(f"/at-home/server/{chapter_id}")
        base = data["baseUrl"]
        ch = data["chapter"]
        h = ch["hash"]
        seg = "data-saver" if data_saver else "data"
        files = ch["dataSaver" if data_saver else "data"]
        return [Page(url=f"{base}/{seg}/{h}/{f}", index=i) for i, f in enumerate(files)]

    def cover_url(self, manga: Manga, *, size: int = 512) -> str | None:
        if not manga.cover_file_name:
            return None
        return f"{UPLOADS}/covers/{manga.id}/{manga.cover_file_name}.{size}.jpg"

    @property
    def is_logged_in(self) -> bool:
        return self._session is not None

    async def login(self, *, client_id: str, client_secret: str,
                    username: str, password: str) -> None:
        self._session = await auth.login(
            self._client.http, client_id=client_id, client_secret=client_secret,
            username=username, password=password,
        )
        tokens.save_session(self._session)

    def logout(self) -> None:
        self._session = None
        tokens.clear_session()

    async def _auth_headers(self) -> dict:
        if self._session is None:
            raise RuntimeError("not logged in")
        if time.time() >= self._session.expires_at:
            self._session = await auth.refresh(self._client.http, self._session)
            tokens.save_session(self._session)
        return {"Authorization": f"Bearer {self._session.access_token}"}

    async def get_reading_statuses(self) -> dict[str, str]:
        data = await self._client.get_json("/manga/status", headers=await self._auth_headers())
        return data.get("statuses", {}) or {}

    async def get_follow_ids(self) -> list[str]:
        ids: list[str] = []
        offset = 0
        while True:
            data = await self._client.get_json(
                "/user/follows/manga",
                params=[("limit", 100), ("offset", offset)],
                headers=await self._auth_headers(),
            )
            items = data.get("data", [])
            ids.extend(it["id"] for it in items)
            offset += len(items)
            if offset >= data.get("total", 0) or not items:
                break
        return ids

    async def get_manga_batch(self, ids: list[str]) -> list[Manga]:
        out: list[Manga] = []
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            params = [("limit", 100), ("includes[]", "cover_art")]
            params += [("ids[]", mid) for mid in chunk]
            data = await self._client.get_json("/manga", params=params)
            out.extend(self._to_manga(item) for item in data.get("data", []))
        return out

    async def aclose(self) -> None:
        await self._client.aclose()

    def _to_manga(self, item: dict) -> Manga:
        attrs = item.get("attributes", {})
        cover = None
        for rel in item.get("relationships", []):
            if rel.get("type") == "cover_art":
                cover = (rel.get("attributes") or {}).get("fileName")
        tags = tuple(
            _pick((t.get("attributes") or {}).get("name", {}))
            for t in attrs.get("tags", [])
        )
        return Manga(
            id=item["id"],
            title=_pick(attrs.get("title", {})),
            description=_pick(attrs.get("description", {})),
            status=attrs.get("status") or "",
            tags=tuple(t for t in tags if t),
            cover_file_name=cover,
            content_rating=attrs.get("contentRating") or "",
        )
