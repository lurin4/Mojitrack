def test_yearly_heatmap_includes_leap_day_and_only_owned_logs(account):
    media = account.post("/api/media", json={"title": "Calendar novel"}).json()
    account.post("/api/logs", json={"media_id": media["id"], "date": "2024-02-29", "chars": 1200})
    leap = account.get("/api/stats/daily?year=2024").json()
    assert len(leap) == 366
    assert leap[0]["date"] == "2024-01-01"
    assert leap[-1]["date"] == "2024-12-31"
    assert next(row for row in leap if row["date"] == "2024-02-29")["chars"] == 1200
    ordinary = account.get("/api/stats/daily?year=2025").json()
    assert len(ordinary) == 365
    assert sum(row["chars"] for row in ordinary) == 0
    account.post("/api/logout")
    account.post("/api/register", json={"username": "another", "password": "another-test-password"})
    assert sum(row["chars"] for row in account.get("/api/stats/daily?year=2024").json()) == 0


def test_year_validation_and_rolling_chart_compatibility(account):
    assert account.get("/api/stats/daily?year=0").status_code == 422
    assert account.get("/api/stats/daily?year=10000").status_code == 422
    assert len(account.get("/api/stats/daily?days=30").json()) == 30
