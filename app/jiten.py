import asyncio
import time
from email.utils import parsedate_to_datetime

import httpx
from cachetools import TTLCache
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas import MediaSnapshot

BASE = "https://api.jiten.moe"
cache = TTLCache(maxsize=500, ttl=86400)
lock = asyncio.Lock()
last_request = 0.0
blocked_until = 0.0


async def fetch(path, params=None, refresh=False):
    global last_request, blocked_until
    key = (path, tuple(sorted((params or {}).items())))
    async with lock:
        if not refresh and key in cache:
            return cache[key]
        remaining = blocked_until - time.time()
        if remaining > 0:
            raise HTTPException(429, "Jiten is rate limited; try again later", headers={"Retry-After": str(int(remaining) + 1)})
        await asyncio.sleep(max(0, 0.5 - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "reading-site/0.1"}) as client:
                response = await client.get(BASE + path, params=params)
            if response.status_code == 429:
                retry = response.headers.get("Retry-After", "60")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = parsedate_to_datetime(retry).timestamp() - time.time()
                    except (ValueError, TypeError, OverflowError):
                        delay = 60
                delay = max(1, min(delay, 86400))
                blocked_until = time.time() + delay
                raise HTTPException(429, "Jiten is rate limited; try again later", headers={"Retry-After": str(int(delay))})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("Expected an object")
        except (httpx.HTTPError, ValueError, TypeError):
            raise HTTPException(502, "Jiten is unavailable or returned an unexpected response")
        cache[key] = data
        return data


def normalize(deck):
    if not isinstance(deck, dict) or not deck.get("deckId"):
        raise HTTPException(502, "Jiten's response format changed")
    values = {
        "jiten_id": deck["deckId"],
        "media_type": {4: "novel", 7: "visual_novel", 8: "novel", 9: "manga"}.get(deck.get("mediaType"), "other"),
        "cover_url": deck.get("coverName") or None,
        "title": deck.get("originalTitle") or deck.get("romajiTitle") or deck.get("englishTitle") or f"Jiten {deck['deckId']}",
        "total_chars": deck.get("characterCount") or None,
        "difficulty": deck.get("difficultyRaw", deck.get("difficulty")),
        "unique_words": deck.get("uniqueWordCount"), "unique_kanji": deck.get("uniqueKanjiCount"),
    }
    try:
        validated = MediaSnapshot.model_validate(values)
    except ValidationError:
        raise HTTPException(502, "Jiten returned invalid title statistics")
    return validated.model_dump(exclude={"status"})


async def search(query, offset=0, media_type="novel"):
    payload = await fetch("/api/media-deck/get-media-decks", {
        "titleFilter": query, "mediaType": {"novel": 4, "visual_novel": 7}[media_type], "offset": offset,
    })
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise HTTPException(502, "Jiten's search response format changed")
    return {"items": [normalize(row) for row in rows], "offset": offset, "has_more": len(rows) == 50}


async def detail(deck_id, refresh=False):
    payload = await fetch(f"/api/media-deck/{deck_id}/detail", refresh=refresh)
    data = payload.get("data")
    if not data:
        raise HTTPException(404, "That Jiten title was not found")
    deck = data.get("mainDeck") if isinstance(data, dict) else None
    if not deck:
        raise HTTPException(502, "Jiten's detail response format changed")
    return normalize(deck)
