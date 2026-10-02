from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.auth import DB, CurrentUser
from app.models import Media, ReadingLog
from app.schemas import LogInput
from app.stats import today_for

router = APIRouter(prefix="/api/logs")


def owned(db, model, item_id, user):
    item = db.scalar(select(model).where(model.id == item_id, model.user_id == user.id))
    if item is None:
        raise HTTPException(404, "Not found")
    return item


def log_data(log):
    return {key: getattr(log, key) for key in ("id", "media_id", "date", "chars", "minutes")}


def validate_log(data, db, user):
    owned(db, Media, data.media_id, user)
    if data.date > today_for(user):
        raise HTTPException(422, "Reading dates cannot be in the future")


@router.get("")
def list_logs(user: CurrentUser, db: DB, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    rows = db.scalars(select(ReadingLog).where(ReadingLog.user_id == user.id)
                      .order_by(ReadingLog.date.desc(), ReadingLog.id.desc()).offset(offset).limit(limit))
    return [log_data(row) for row in rows]


@router.post("", status_code=201)
def add_log(data: LogInput, user: CurrentUser, db: DB):
    validate_log(data, db, user)
    log = ReadingLog(user_id=user.id, **data.model_dump())
    db.add(log)
    db.commit()
    return log_data(log)


@router.patch("/{log_id}")
def edit_log(log_id: int, data: LogInput, user: CurrentUser, db: DB):
    log = owned(db, ReadingLog, log_id, user)
    validate_log(data, db, user)
    for key, value in data.model_dump().items():
        setattr(log, key, value)
    db.commit()
    return log_data(log)


@router.delete("/{log_id}")
def delete_log(log_id: int, user: CurrentUser, db: DB):
    db.delete(owned(db, ReadingLog, log_id, user))
    db.commit()
    return {"ok": True}
