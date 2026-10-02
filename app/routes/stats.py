from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.auth import DB, CurrentUser
from app.models import Media, ReadingLog
from app.routes.logs import owned
from app.stats import daily_rows, summary, today_for

router = APIRouter(prefix="/api/stats")


def user_logs(db, user):
    return list(db.scalars(select(ReadingLog).where(ReadingLog.user_id == user.id)))


@router.get("/summary")
def get_summary(user: CurrentUser, db: DB):
    return summary(user_logs(db, user), user, today_for(user))


@router.get("/daily")
def get_daily(user: CurrentUser, db: DB, days: int = Query(365, ge=1, le=366),
              year: int | None = Query(None, ge=1900, le=9998)):
    if year is not None:
        start, end = date(year, 1, 1), date(year, 12, 31)
        return daily_rows(user_logs(db, user), end, (end - start).days + 1)
    return daily_rows(user_logs(db, user), today_for(user), days)


@router.get("/media/{media_id}")
def get_progress(media_id: int, user: CurrentUser, db: DB):
    owned(db, Media, media_id, user)
    logs = db.scalars(select(ReadingLog).where(ReadingLog.user_id == user.id, ReadingLog.media_id == media_id,
                                              ReadingLog.date <= today_for(user)).order_by(ReadingLog.date))
    cumulative = 0
    dates = {}
    for log in logs:
        cumulative += log.chars
        dates[log.date.isoformat()] = cumulative
    return [{"date": day, "chars": chars} for day, chars in dates.items()]
