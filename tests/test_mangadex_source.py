import httpx
import respx
import pytest
from mango.sources.mangadex.source import MangaDexSource


@respx.mock
async def test_search_parses_titles_and_cover():
    respx.get("https://api.mangadex.org/manga").mock(
        return_value=httpx.Response(200, json={
            "data": [{
                "id": "m1",
                "attributes": {
                    "title": {"en": "Test Manga"},
                    "description": {"en": "desc"},
                    "status": "ongoing",
                    "tags": [{"attributes": {"name": {"en": "Romance"}}}],
                },
                "relationships": [
                    {"type": "cover_art", "attributes": {"fileName": "c1.jpg"}}
                ],
            }]
        })
    )
    src = MangaDexSource()
    results = await src.search("test")
    await src.aclose()
    m = results[0]
    assert m.id == "m1" and m.title == "Test Manga"
    assert m.tags == ("Romance",) and m.cover_file_name == "c1.jpg"
    assert src.cover_url(m) == "https://uploads.mangadex.org/covers/m1/c1.jpg.512.jpg"


@respx.mock
async def test_get_pages_builds_at_home_urls():
    respx.get("https://api.mangadex.org/at-home/server/ch1").mock(
        return_value=httpx.Response(200, json={
            "baseUrl": "https://uploads.example.org",
            "chapter": {"hash": "HASH", "data": ["p1.png", "p2.png"], "dataSaver": ["s1.jpg"]},
        })
    )
    src = MangaDexSource()
    pages = await src.get_pages("ch1")
    await src.aclose()
    assert [p.url for p in pages] == [
        "https://uploads.example.org/data/HASH/p1.png",
        "https://uploads.example.org/data/HASH/p2.png",
    ]
    assert [p.index for p in pages] == [0, 1]
