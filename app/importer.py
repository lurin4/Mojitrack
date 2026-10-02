"""Import the supplied Discord bot's user map and documented export formats."""
import hashlib
import json
from datetime import datetime

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.models import ImportReceipt, Media, ReadingLog
from app.schemas import LogInput, MediaInput, MediaSnapshot
from app.stats import today_for

MAX_ROWS = 10000


def import_data(payload, user, db, source_user=None, dry_run=True, import_goal=False):
    source_user = source_user or None
    canonical = json.dumps(payload, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    legacy_checksum = hashlib.sha256(
        (str(source_user) + canonical).encode()).hexdigest()
    if source_user:
        if not isinstance(payload, dict) or source_user not in payload:
            raise HTTPException(
                422, "Source user ID was not found at the top level")
        payload = payload[source_user]
    elif isinstance(payload, dict) and "logs" not in payload:
        raise HTTPException(
            422, "For your bot's reading_data.json, enter your Discord user ID in Source user ID")
    # Changes to another Discord user's records must not allow this user's logs to be imported twice.
    selected = json.dumps({"source_user": source_user, "data": payload}, sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)
    checksum = hashlib.sha256(selected.encode()).hexdigest()
    if db.scalar(select(ImportReceipt).where(ImportReceipt.user_id == user.id,
                                             ImportReceipt.digest.in_([checksum, legacy_checksum]))):
        raise HTTPException(
            409, "This user's selected import has already been applied")
    exported = isinstance(payload, dict) and payload.get(
        "format") == "reading-site-v1"
    rows = payload if isinstance(payload, list) else payload.get(
        "logs") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise HTTPException(
            422, "Expected a list of up to 10,000 logs, or an object with a logs list. See examples.")
    raw_media = payload.get("media", []) if exported else []
    if not isinstance(raw_media, list) or len(raw_media) > MAX_ROWS:
        raise HTTPException(422, "Invalid media list")
    prepared_media = {}
    prepared_logs = []
    today = today_for(user)
    saved_goal = payload.get("daily_goal") if isinstance(
        payload, dict) and not exported else None
    goal_to_import = None
    if import_goal and isinstance(payload, dict) and "daily_goal" in payload and not exported:
        if type(saved_goal) is not int or not 1 <= saved_goal <= 1_000_000_000:
            raise HTTPException(
                422, "The saved daily_goal must be a positive integer up to 1,000,000,000. Uncheck goal import to keep your current goal.")
        goal_to_import = saved_goal
    try:
        for item in raw_media:
            key = item["id"]
            if type(key) is not int or key in prepared_media:
                raise ValueError("Media IDs must be unique integers")
            validated = MediaSnapshot.model_validate(
                {k: v for k, v in item.items() if k != "id"})
            prepared_media[key] = validated.model_dump()
        for index, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                raise TypeError(f"Row {index} must be an object")
            if exported:
                key = row["media_id"]
                if key not in prepared_media:
                    raise ValueError(f"Row {index} references missing media")
            else:
                allowed = {"title", "media", "media_type",
                           "date", "chars", "characters", "minutes"}
                if set(row) - allowed:
                    raise ValueError(
                        f"Row {index} has unknown fields; adapt it to the documented format")
                title = row.get("title", row.get("media"))
                validated = MediaInput(
                    title=title, media_type=row.get("media_type", "novel"))
                key = (validated.title, validated.media_type)
                prepared_media[key] = validated.model_dump()
            # The bot's strptime accepts dates without zero padding; normalize only their representation.
            day = row["date"] if exported else datetime.strptime(row["date"], "%Y-%m-%d").date()  # noqa: DTZ007 -- Calendar date only, not a timestamp.
            chars = row.get("chars", row.get("characters"))
            if type(chars) is not int or chars <= 0:
                raise ValueError(
                    f"Row {index}: chars must be a positive integer. The bot allowed zero/negative entries; this site does not silently drop them.")
            log = LogInput(media_id=1, date=day, chars=chars,
                           minutes=row.get("minutes"))
            if log.date > today:
                raise ValueError(f"Row {index} is in the future")
            prepared_logs.append((key, log.model_dump(exclude={"media_id"})))
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            422, f"Import rejected; no changes made: {str(exc)[:600]}")
    counts = {"logs": len(prepared_logs), "titles": len(prepared_media), "dry_run": dry_run,
              "total_chars": sum(values["chars"] for _, values in prepared_logs),
              "daily_goal": goal_to_import, "current_daily_goal": user.daily_goal}
    jiten_ids = [m.get("jiten_id")
                 for m in prepared_media.values() if m.get("jiten_id")]
    if len(jiten_ids) != len(set(jiten_ids)):
        raise HTTPException(422, "Duplicate Jiten IDs in this file")
    if jiten_ids and db.scalar(select(Media.id).where(Media.user_id == user.id, Media.jiten_id.in_(jiten_ids)).limit(1)):
        raise HTTPException(
            409, "One or more Jiten titles already exist. Restore into an empty account.")
    if dry_run:
        return counts
    if not prepared_media and not prepared_logs and goal_to_import is None:
        raise HTTPException(422, "Nothing to import")
    mapping = {}
    for key, values in prepared_media.items():
        # Export restore preserves distinct titles; bot imports can match a unique existing title.
        matches = [] if exported else list(db.scalars(select(Media).where(
            Media.user_id == user.id, Media.title == values["title"], Media.media_type == values["media_type"])))
        if len(matches) > 1:
            raise HTTPException(
                409, f"Ambiguous library title: {values['title']}")
        media = matches[0] if matches else Media(user_id=user.id, **values)
        db.add(media)
        db.flush()
        mapping[key] = media.id
    for key, values in prepared_logs:
        db.add(ReadingLog(user_id=user.id, media_id=mapping[key], **values))
    if goal_to_import is not None:
        user.daily_goal = goal_to_import
    db.add(ImportReceipt(user_id=user.id, digest=checksum))
    db.commit()
    return counts
