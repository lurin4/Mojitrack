import os

os.environ["SECRET_KEY"] = "test-only-secret-0123456789-abcdefghijklmnopqrstuvwxyz"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ORIGIN"] = "http://testserver"
os.environ["COOKIE_SECURE"] = "false"
os.environ["REGISTRATION_MODE"] = "open"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import attempts
from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)

    def database():
        with session() as db:
            yield db

    app.dependency_overrides[get_db] = database
    attempts.clear()
    with TestClient(app, headers={"X-Reading-Site": "1"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def account(client):
    response = client.post("/api/register", json={"username": "reader", "password": "long-test-password"})
    assert response.status_code == 201
    return client
