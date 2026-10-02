import csv
import io
import json

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.auth import DB, CurrentUser
from app.counting import analyze_text
from app.importer import import_data
from app.models import Media, ReadingLog
from app.routes.logs import log_data
from app.routes.media import media_data
from app.schemas import CountInput

router = APIRouter(prefix="/api")


@router.get("/export.json")
def export_json(user: CurrentUser, db: DB):
    payload = {"format": "reading-site-v1", "media": [media_data(m) for m in db.scalars(select(Media).where(Media.user_id == user.id))],
               "logs": [log_data(row) for row in db.scalars(select(ReadingLog).where(ReadingLog.user_id == user.id))],
               "jiten_attribution": "Jiten (https://jiten.moe), derived statistics CC BY-SA 4.0"}
    return Response(json.dumps(jsonable_encoder(payload), ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="reading-data.json"'})


@router.get("/export.csv")
def export_csv(user: CurrentUser, db: DB):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["date", "title", "media_type", "chars", "minutes"])
    rows = db.execute(select(ReadingLog, Media).join(Media).where(ReadingLog.user_id == user.id).order_by(ReadingLog.date))
    for log, media in rows:
        title = media.title
        if title.lstrip().startswith(("=", "+", "-", "@")) or title.startswith(("\t", "\r", "\n")):
            title = "'" + title
        writer.writerow([log.date.isoformat(), title, media.media_type, log.chars, log.minutes or ""])
    return Response("\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="reading-data.csv"'})


@router.post("/import/bot-json")
async def import_json(request: Request, user: CurrentUser, db: DB, dry_run: bool = True,
                      source_user: str | None = Query(None, max_length=80), import_goal: bool = False):
    try:
        payload = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "The file must contain valid UTF-8 JSON")
    return import_data(payload, user, db, source_user, dry_run, import_goal)


@router.post("/count")
def count_text(data: CountInput, user: CurrentUser):
    return analyze_text(data.text)
