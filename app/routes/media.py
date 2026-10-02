import math
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app import jiten
from app.auth import DB, CurrentUser
from app.models import Media, ReadingLog
from app.routes.logs import owned
from app.schemas import MediaInput
from app.stats import today_for

router = APIRouter(prefix="/api")


def media_data(media):
    return {key: getattr(media, key) for key in (
        "id", "title", "media_type", "total_chars", "status", "jiten_id", "cover_url", "difficulty", "unique_words", "unique_kanji"
    )}


@router.get("/media")
def library(user: CurrentUser, db: DB):
    today = today_for(user)
    totals = dict(db.execute(select(ReadingLog.media_id, func.sum(ReadingLog.chars)).where(
        ReadingLog.user_id == user.id, ReadingLog.date <= today).group_by(ReadingLog.media_id)).all())
    recent = dict(db.execute(select(ReadingLog.media_id, func.sum(ReadingLog.chars)).where(
        ReadingLog.user_id == user.id, ReadingLog.date <= today, ReadingLog.date >= today - timedelta(days=29)
    ).group_by(ReadingLog.media_id)).all())
    result = []
    for media in db.scalars(select(Media).where(Media.user_id == user.id).order_by(Media.id.desc())):
        read = totals.get(media.id, 0)
        remaining = max(0, media.total_chars - read) if media.total_chars else None
        rate = recent.get(media.id, 0) / 30
        days = math.ceil(remaining / rate) if remaining is not None and rate else (0 if remaining == 0 else None)
        result.append({**media_data(media), "read_chars": read, "days_left": days,
                       "estimated_finish": (today + timedelta(days=days)).isoformat() if days is not None and days < 36500 else None})
    return result


@router.post("/media", status_code=201)
def add_media(data: MediaInput, user: CurrentUser, db: DB):
    media = Media(user_id=user.id, **data.model_dump())
    db.add(media)
    db.commit()
    return media_data(media)


@router.patch("/media/{media_id}")
def edit_media(media_id: int, data: MediaInput, user: CurrentUser, db: DB):
    media = owned(db, Media, media_id, user)
    for key, value in data.model_dump().items():
        setattr(media, key, value)
    db.commit()
    return media_data(media)


@router.delete("/media/{media_id}")
def delete_media(media_id: int, user: CurrentUser, db: DB):
    media = owned(db, Media, media_id, user)
    if db.scalar(select(ReadingLog.id).where(ReadingLog.media_id == media.id).limit(1)):
        raise HTTPException(409, "This title has reading logs. Delete those logs first, or mark it dropped.")
    db.delete(media)
    db.commit()
    return {"ok": True}


@router.get("/jiten/search")
async def search_jiten(user: CurrentUser, q: str = Query(min_length=1, max_length=200),
                       offset: int = Query(0, ge=0, le=10000), media_type: Literal["novel", "visual_novel"] = "novel"):
    if not q.strip():
        raise HTTPException(422, "Enter a title")
    return await jiten.search(q.strip(), offset, media_type)


@router.post("/media/from-jiten/{deck_id}", status_code=201)
async def from_jiten(deck_id: int, user: CurrentUser, db: DB):
    if deck_id <= 0:
        raise HTTPException(422, "Invalid deck ID")
    if db.scalar(select(Media.id).where(Media.user_id == user.id, Media.jiten_id == deck_id)):
        raise HTTPException(409, "This title is already in your library")
    values = await jiten.detail(deck_id)
    media = Media(user_id=user.id, **values)
    db.add(media)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This title is already in your library")
    return media_data(media)


@router.post("/media/{media_id}/refresh")
async def refresh_media(media_id: int, user: CurrentUser, db: DB):
    media = owned(db, Media, media_id, user)
    if not media.jiten_id:
        raise HTTPException(422, "This is a manually added title")
    values = await jiten.detail(media.jiten_id, refresh=True)
    for key in ("total_chars", "difficulty", "unique_words", "unique_kanji", "cover_url", "media_type"):
        setattr(media, key, values[key])
    db.commit()
    return media_data(media)


@router.post("/media/{media_id}/link-jiten/{deck_id}")
async def link_jiten(media_id: int, deck_id: int, user: CurrentUser, db: DB, merge: bool = False):
    source = owned(db, Media, media_id, user)
    if deck_id <= 0:
        raise HTTPException(422, "Invalid deck ID")
    target = db.scalar(select(Media).where(Media.user_id == user.id, Media.jiten_id == deck_id))
    if target and target.id != source.id and not merge:
        raise HTTPException(409, "This Jiten title is already in your library. Confirm combining the entries first.")
    values = await jiten.detail(deck_id)
    if target and target.id != source.id:
        # Reassign the original logs rather than copying them or changing their dates/counts.
        db.execute(update(ReadingLog).where(ReadingLog.user_id == user.id, ReadingLog.media_id == source.id)
                   .values(media_id=target.id))
        db.delete(source)
    else:
        target = source
    for key, value in values.items():
        setattr(target, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "The library changed while linking. Reload and try again.")
    return media_data(target)
