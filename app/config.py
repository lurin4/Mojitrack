from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    secret_key: str
    database_url: str = "sqlite:///./data/reading.db"
    app_origin: str = "http://localhost:8000"
    cookie_secure: bool = False
    registration_mode: Literal["first_user", "open", "closed"] = "first_user"

    @field_validator("secret_key")
    @classmethod
    def valid_secret(cls, value):
        if len(value) < 32 or value.startswith("replace-"):
            raise ValueError(
                "Set SECRET_KEY to a fresh random secret of at least 32 characters")
        return value

    @field_validator("app_origin")
    @classmethod
    def valid_origin(cls, value):
        from urllib.parse import urlsplit
        value = value.rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path:
            raise ValueError(
                "APP_ORIGIN must be an origin such as https://reading.example.com")
        if parsed.query or parsed.fragment or parsed.username:
            raise ValueError(
                "APP_ORIGIN cannot include credentials, a query or a fragment")
        return value

    @model_validator(mode="after")
    def secure_origin(self):
        if self.app_origin.startswith("https://") and not self.cookie_secure:
            raise ValueError("HTTPS requires COOKIE_SECURE=true")
        return self


@lru_cache
def settings():
    return Settings()
