import pytest
from fastapi import HTTPException

from app import jiten


@pytest.fixture
def jiten_detail(monkeypatch):
    async def detail(deck_id):
        return jiten.normalize({"deckId": deck_id, "originalTitle": "Official title", "mediaType": 7,
                                "characterCount": 90000, "coverName": "https://cdn.jiten.moe/42/cover.jpg"})
    monkeypatch.setattr(jiten, "detail", detail)


def add_logged_title(account, title, status="reading"):
    item = account.post("/api/media", json={"title": title, "status": status}).json()
    log = account.post("/api/logs", json={"media_id": item["id"], "date": "2020-01-01",
                                          "chars": 1234, "minutes": 15}).json()
    return item, log


def test_link_keeps_log_identity_and_status(account, jiten_detail):
    item, log = add_logged_title(account, "Imported title", "finished")
    result = account.post(f"/api/media/{item['id']}/link-jiten/42")
    assert result.status_code == 200
    linked = result.json()
    assert linked["id"] == item["id"]
    assert linked["title"] == "Official title"
    assert linked["status"] == "finished"
    assert linked["media_type"] == "visual_novel"
    assert linked["cover_url"].endswith("/42/cover.jpg")
    assert account.get("/api/logs").json() == [log]
    assert account.post(f"/api/media/{item['id']}/link-jiten/42").status_code == 200
    assert len(account.get("/api/logs").json()) == 1


def test_merge_requires_confirmation_and_preserves_both_logs(account, jiten_detail):
    source, old_log = add_logged_title(account, "Old title")
    target, target_log = add_logged_title(account, "Already linked", "finished")
    assert account.post(f"/api/media/{target['id']}/link-jiten/42").status_code == 200
    url = f"/api/media/{source['id']}/link-jiten/42"
    assert account.post(url).status_code == 409
    assert len(account.get("/api/media").json()) == 2
    result = account.post(url + "?merge=true")
    assert result.status_code == 200
    assert result.json()["id"] == target["id"]
    assert result.json()["status"] == "finished"
    remaining = account.get("/api/media").json()
    assert len(remaining) == 1
    assert remaining[0]["read_chars"] == 2468
    logs = account.get("/api/logs").json()
    assert {row["id"] for row in logs} == {old_log["id"], target_log["id"]}
    assert all(row["media_id"] == target["id"] and row["chars"] == 1234 and row["minutes"] == 15
               and row["date"] == "2020-01-01" for row in logs)


def test_failed_lookup_does_not_change_history(account, monkeypatch):
    item, log = add_logged_title(account, "Keep this")
    async def unavailable(deck_id):
        raise HTTPException(502, "Unavailable")
    monkeypatch.setattr(jiten, "detail", unavailable)
    assert account.post(f"/api/media/{item['id']}/link-jiten/42").status_code == 502
    assert account.get("/api/media").json()[0]["title"] == "Keep this"
    assert account.get("/api/logs").json() == [log]
    assert account.post(f"/api/media/{item['id']}/link-jiten/0").status_code == 422


def test_link_requires_ownership(account, jiten_detail):
    item, _ = add_logged_title(account, "Private")
    account.post("/api/logout")
    account.post("/api/register", json={"username": "another_reader", "password": "long-test-password"})
    assert account.post(f"/api/media/{item['id']}/link-jiten/42?merge=true").status_code == 404
