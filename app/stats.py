from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def today_for(user):
    return datetime.now(ZoneInfo(user.timezone)).date()


def streak(totals, today, target):
    day = today if totals.get(today, 0) >= target else today - timedelta(days=1)
    length = 0
    while totals.get(day, 0) >= target:
        length += 1
        day -= timedelta(days=1)
    return length


def daily_rows(logs, today, days):
    grouped = defaultdict(lambda: defaultdict(int))
    for log in logs:
        grouped[log.date][str(log.media_id)] += log.chars
    result = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        media = dict(grouped[day])
        result.append({"date": day.isoformat(), "chars": sum(media.values()), "media": media})
    return result


def summary(logs, user, today):
    totals = defaultdict(int)
    by_media = defaultdict(int)
    timed_chars = minutes = 0
    for log in logs:
        if log.date > today:
            continue
        totals[log.date] += log.chars
        by_media[log.media_id] += log.chars
        if log.minutes:
            timed_chars += log.chars
            minutes += log.minutes
    total = sum(totals.values())
    elapsed = (today - min(totals)).days + 1 if totals else 0
    best = max(totals, key=totals.get) if totals else None
    monday = today - timedelta(days=today.weekday())
    return {
        "today": today.isoformat(), "today_chars": totals.get(today, 0),
        "daily_goal": user.daily_goal, "total_chars": total, "reading_days": len(totals),
        "reading_streak": streak(totals, today, 1), "goal_streak": streak(totals, today, user.daily_goal),
        "best_day": best.isoformat() if best else None, "best_day_chars": totals[best] if best else 0,
        "average_calendar_day": round(total / elapsed, 1) if elapsed else 0,
        "average_reading_day": round(total / len(totals), 1) if totals else 0,
        "chars_per_hour": round(timed_chars * 60 / minutes) if minutes else None,
        "weekly_chars": sum(n for d, n in totals.items() if monday <= d <= today),
        "monthly_chars": sum(n for d, n in totals.items() if d.replace(day=1) == today.replace(day=1)),
        "by_media": dict(by_media),
    }
