from datetime import date, timedelta
from types import SimpleNamespace

from app.stats import daily_rows, streak, summary


def test_streak_grace_and_gap():
    today = date(2026, 3, 1)
    totals = {today - timedelta(days=1): 1500, today - timedelta(days=2): 500}
    assert streak(totals, today, 1) == 2
    assert streak(totals, today, 1000) == 1
    assert streak(totals, today + timedelta(days=1), 1) == 0
    totals[today] = 1000
    assert streak(totals, today, 1000) == 2


def test_leap_day_heatmap_and_multiple_sessions():
    today = date(2024, 3, 1)
    logs = [SimpleNamespace(date=date(2024, 2, 29), media_id=1, chars=600, minutes=10),
            SimpleNamespace(date=date(2024, 2, 29), media_id=1, chars=500, minutes=None)]
    rows = daily_rows(logs, today, 3)
    assert [r["date"] for r in rows] == ["2024-02-28", "2024-02-29", "2024-03-01"]
    assert rows[1]["chars"] == 1100
    assert rows[1]["media"] == {"1": 1100}
    assert rows[2]["chars"] == 0
    result = summary(logs, SimpleNamespace(daily_goal=1000), today)
    assert result["goal_streak"] == 1
    assert result["average_calendar_day"] == 550
    assert result["average_reading_day"] == 1100
    assert result["chars_per_hour"] == 3600


def test_empty_and_future_data():
    user = SimpleNamespace(daily_goal=1000)
    today = date(2026, 1, 1)
    assert summary([], user, today)["total_chars"] == 0
    log = SimpleNamespace(date=today + timedelta(days=1), chars=999, media_id=1, minutes=None)
    assert summary([log], user, today)["total_chars"] == 0
