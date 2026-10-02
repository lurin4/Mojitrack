from datetime import UTC, datetime, timedelta

from app.config import settings


def add_title(client):
    response = client.post("/api/media", json={"title": "Test novel", "total_chars": 20000})
    assert response.status_code == 201
    return response.json()["id"]


def test_accounts_are_isolated(account):
    media_id = add_title(account)
    row = {"media_id": media_id, "date": "2024-01-01", "chars": 1000}
    log = account.post("/api/logs", json=row).json()
    account.post("/api/logout")
    account.post("/api/register", json={"username": "second", "password": "another-long-password"})
    assert account.get("/api/media").json() == []
    assert account.get("/api/logs").json() == []
    assert account.post("/api/logs", json=row).status_code == 404
    assert account.patch(f"/api/logs/{log['id']}", json=row).status_code == 404
    assert account.delete(f"/api/media/{media_id}").status_code == 404


def test_edit_delete_and_validation(account):
    media_id = add_title(account)
    data = {"media_id": media_id, "date": "2024-01-01", "chars": 100}
    response = account.post("/api/logs", json=data)
    assert response.status_code == 201
    log_id = response.json()["id"]
    assert account.post("/api/logs", json={**data, "chars": -1}).status_code == 422
    assert account.post("/api/logs", json={**data, "date": (datetime.now(UTC).date()+timedelta(days=3)).isoformat()}).status_code == 422
    assert account.patch(f"/api/logs/{log_id}", json={**data, "chars": 750}).status_code == 200
    assert account.get("/api/stats/summary").json()["total_chars"] == 750
    assert account.delete(f"/api/media/{media_id}").status_code == 409
    assert account.delete(f"/api/logs/{log_id}").status_code == 200
    assert account.get("/api/stats/summary").json()["total_chars"] == 0
    assert account.delete(f"/api/media/{media_id}").status_code == 200


def test_csrf_and_logout_revocation(account):
    cookie = account.cookies.get("session")
    assert account.post("/api/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert account.post("/api/logout", headers={"X-Reading-Site": ""}).status_code == 403
    assert account.post("/api/logout").status_code == 200
    account.cookies.set("session", cookie)
    assert account.get("/api/me").status_code == 401


def test_registration_can_close(client):
    config = settings()
    previous = config.registration_mode
    config.registration_mode = "first_user"
    try:
        assert client.post("/api/register", json={"username": "one", "password": "long-test-password"}).status_code == 201
        assert client.post("/api/register", json={"username": "two", "password": "long-test-password"}).status_code == 403
    finally:
        config.registration_mode = previous


def test_import_preview_atomicity_and_duplicate(account):
    data = [{"title": "Imported novel", "date": "2024-01-01", "chars": 200}]
    assert account.post("/api/import/bot-json", json=data).json()["dry_run"] is True
    assert account.get("/api/logs").json() == []
    invalid = data + [{"title": "Broken", "date": "bad", "chars": 50}]
    assert account.post("/api/import/bot-json?dry_run=false", json=invalid).status_code == 422
    assert account.get("/api/media").json() == []
    assert account.post("/api/import/bot-json?dry_run=false", json=data).status_code == 200
    assert account.post("/api/import/bot-json?dry_run=false", json=data).status_code == 409
    assert account.get("/api/stats/summary").json()["total_chars"] == 200


def test_token_and_public_profile(account):
    token = account.post("/api/token").json()["token"]
    assert account.get("/api/public/reader").status_code == 404
    prefs = {"daily_goal": 1500, "weekly_goal": 9000, "monthly_goal": 40000, "timezone": "Asia/Tokyo", "public_profile": True}
    assert account.patch("/api/me", json=prefs).status_code == 200
    public = account.get("/api/public/reader").json()
    assert "by_media" not in public
    account.post("/api/logout")
    headers = {"Authorization": f"Bearer {token}"}
    assert account.get("/api/me", headers=headers).status_code == 200
    assert account.delete("/api/token", headers=headers).status_code == 200
    assert account.get("/api/me", headers=headers).status_code == 401


def test_csv_formula_escape_and_counter(account):
    media_id = account.post("/api/media", json={"title": "=1+1"}).json()["id"]
    account.post("/api/logs", json={"media_id": media_id, "date": "2024-01-01", "chars": 10})
    assert "'=1+1" in account.get("/api/export.csv").text
    result = account.post("/api/count", json={"text": "\u732b\u304c\u597d\u304d\u3002 ABC123"}).json()
    assert result["chars"] == 5
    assert result["punctuation"] == 1
