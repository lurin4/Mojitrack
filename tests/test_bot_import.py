import copy


def bot_data():
    return {
        "123456789012345678": {
            "daily_goal": 2500,
            "logs": [
                {"date": "2024-01-01", "media": "Example Novel", "chars": 1000},
                {"date": "2024-1-2", "media": "Example Novel", "chars": 750},
            ],
        },
        "987654321098765432": {
            "daily_goal": 100,
            "logs": [{"date": "2024-01-01", "media": "Other User's Book", "chars": 99999}],
        },
    }


URL = "/api/import/bot-json?source_user=123456789012345678"


def test_bot_preview_and_goal_migration(account):
    preview = account.post(URL + "&import_goal=true", json=bot_data())
    assert preview.status_code == 200
    assert preview.json()["total_chars"] == 1750
    assert preview.json()["daily_goal"] == 2500
    assert account.get("/api/me").json()["daily_goal"] == 1000
    assert account.get("/api/logs").json() == []
    applied = account.post(URL + "&import_goal=true&dry_run=false", json=bot_data())
    assert applied.status_code == 200
    assert account.get("/api/me").json()["daily_goal"] == 2500
    assert account.get("/api/me").json()["weekly_goal"] == 7000
    library = account.get("/api/media").json()
    assert len(library) == 1
    assert library[0]["title"] == "Example Novel"
    assert library[0]["read_chars"] == 1750
    assert account.get("/api/logs").json()[0]["date"] == "2024-01-02"


def test_goal_import_can_be_disabled(account):
    result = account.post(URL + "&dry_run=false", json=bot_data())
    assert result.status_code == 200
    assert account.get("/api/me").json()["daily_goal"] == 1000


def test_other_users_changes_do_not_bypass_duplicate_check(account):
    payload = bot_data()
    assert account.post(URL + "&dry_run=false", json=payload).status_code == 200
    payload["987654321098765432"]["logs"].append({"date": "2024-02-01", "media": "Other", "chars": 30})
    assert account.post(URL + "&dry_run=false", json=payload).status_code == 409
    assert len(account.get("/api/logs").json()) == 2


def test_invalid_legacy_counts_abort_goal_and_logs(account):
    payload = bot_data()
    payload["123456789012345678"]["logs"].append({"date": "2024-02-01", "media": "Correction", "chars": -100})
    result = account.post(URL + "&import_goal=true&dry_run=false", json=payload)
    assert result.status_code == 422
    assert "Row 3" in result.json()["detail"]
    assert account.get("/api/me").json()["daily_goal"] == 1000
    assert account.get("/api/logs").json() == []
    assert account.get("/api/media").json() == []


def test_invalid_goal_can_be_skipped(account):
    payload = bot_data()
    payload["123456789012345678"]["daily_goal"] = 0
    assert account.post(URL + "&import_goal=true", json=payload).status_code == 422
    assert account.post(URL + "&dry_run=false", json=payload).status_code == 200


def test_goal_only_user(account):
    payload = {"123456789012345678": {"daily_goal": 3000, "logs": []}}
    result = account.post(URL + "&import_goal=true&dry_run=false", json=payload)
    assert result.status_code == 200
    assert account.get("/api/me").json()["daily_goal"] == 3000


def test_export_keeps_working(account):
    assert account.post(URL + "&dry_run=false", json=bot_data()).status_code == 200
    payload = copy.deepcopy(account.get("/api/export.json").json())
    account.post("/api/logout")
    account.post("/api/register", json={"username": "restored", "password": "long-test-password"})
    assert account.post("/api/import/bot-json?dry_run=false", json=payload).status_code == 200
