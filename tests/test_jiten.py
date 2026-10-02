import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app import jiten


def test_search_uses_title_filter(monkeypatch):
    async def fake_fetch(path, params=None, refresh=False):
        assert path == "/api/media-deck/get-media-decks"
        assert params == {"titleFilter": "novel", "mediaType": 4, "offset": 50}
        return {"data": [{"deckId": 9, "originalTitle": "Title", "characterCount": 10000}]}
    monkeypatch.setattr(jiten, "fetch", fake_fetch)
    result = asyncio.run(jiten.search("novel", 50))
    assert result["items"][0]["jiten_id"] == 9


def test_empty_detail_is_not_found(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return {"data": None}
    monkeypatch.setattr(jiten, "fetch", fake_fetch)
    with pytest.raises(HTTPException) as error:
        asyncio.run(jiten.detail(999))
    assert error.value.status_code == 404


def test_429_is_handled_before_json(monkeypatch):
    calls = []
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, *args, **kwargs):
            calls.append(1)
            return httpx.Response(429, text="Too many requests.", headers={"Retry-After": "120"})
    monkeypatch.setattr(jiten.httpx, "AsyncClient", Client)
    monkeypatch.setattr(jiten, "lock", asyncio.Lock())
    monkeypatch.setattr(jiten, "blocked_until", 0)
    jiten.cache.clear()

    async def exercise():
        for _ in range(2):
            with pytest.raises(HTTPException) as error:
                await jiten.fetch("/test")
            assert error.value.status_code == 429
    asyncio.run(exercise())
    assert len(calls) == 1
