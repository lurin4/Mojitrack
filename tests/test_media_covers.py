import asyncio

import pytest
from fastapi import HTTPException

from app import jiten


@pytest.mark.parametrize(("kind", "expected"), [(4, "novel"), (7, "visual_novel"), (8, "novel"), (9, "manga"), (99, "other")])
def test_jiten_type_and_cover(kind, expected):
    result = jiten.normalize({"deckId": 42, "mediaType": kind, "coverName": "https://cdn.jiten.moe/42/cover.jpg"})
    assert result["media_type"] == expected
    assert result["cover_url"] == "https://cdn.jiten.moe/42/cover.jpg"


def test_missing_and_invalid_cover():
    assert jiten.normalize({"deckId": 42})["cover_url"] is None
    with pytest.raises(HTTPException):
        jiten.normalize({"deckId": 42, "coverName": "javascript:alert(1)"})


def test_visual_novel_search(monkeypatch):
    async def fetch(path, params=None, refresh=False):
        assert params == {"titleFilter": "Steins", "mediaType": 7, "offset": 0}
        return {"data": []}
    monkeypatch.setattr(jiten, "fetch", fetch)
    assert asyncio.run(jiten.search("Steins", media_type="visual_novel"))["items"] == []


def test_add_refresh_export_cover(account, monkeypatch):
    async def detail(deck_id, refresh=False):
        return jiten.normalize({"deckId": deck_id, "originalTitle": "Test VN", "mediaType": 7,
                                "coverName": f"https://cdn.jiten.moe/{deck_id}/{'new' if refresh else 'cover'}.jpg"})
    monkeypatch.setattr(jiten, "detail", detail)
    response = account.post("/api/media/from-jiten/42")
    assert response.status_code == 201
    item = response.json()
    assert item["media_type"] == "visual_novel"
    assert item["cover_url"].endswith("/cover.jpg")
    response = account.post(f"/api/media/{item['id']}/refresh")
    assert response.status_code == 200
    assert response.json()["cover_url"].endswith("/new.jpg")
    assert account.get("/api/media").json()[0]["cover_url"].endswith("/new.jpg")
    assert account.get("/api/jiten/search?q=test&media_type=invalid").status_code == 422
