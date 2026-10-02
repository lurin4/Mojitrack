def test_export_restore_preserves_library_and_logs(account):
    media = account.post("/api/media", json={"title": "Restorable", "total_chars": 5000, "status": "finished"}).json()
    account.post("/api/logs", json={"media_id": media["id"], "date": "2024-03-01", "chars": 1000, "minutes": 15})
    backup = account.get("/api/export.json").json()
    account.post("/api/logout")
    account.post("/api/register", json={"username": "restore", "password": "long-test-password"})
    result = account.post("/api/import/bot-json?dry_run=false", json=backup)
    assert result.status_code == 200
    library = account.get("/api/media").json()
    assert library[0]["title"] == "Restorable"
    assert library[0]["total_chars"] == 5000
    assert library[0]["status"] == "finished"
    assert library[0]["read_chars"] == 1000
    assert account.get("/api/logs").json()[0]["minutes"] == 15


def test_user_map_requires_explicit_selection(account):
    payload = {"123": {"logs": [{"title": "Selected", "date": "2024-01-01", "chars": 20}]}}
    assert account.post("/api/import/bot-json?dry_run=false", json=payload).status_code == 422
    assert account.post("/api/import/bot-json?dry_run=false&source_user=123", json=payload).status_code == 200
