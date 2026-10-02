from datetime import date as Date
from typing import Annotated, Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Positive = Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Input):
    username: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_]{3,40}$")]
    password: str = Field(min_length=12, max_length=128)


class Preferences(Input):
    daily_goal: Positive
    weekly_goal: Positive
    monthly_goal: Positive
    timezone: str = Field(max_length=80)
    public_profile: bool = False

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use an IANA timezone, e.g. Europe/London")
        return value


class MediaInput(Input):
    title: Title
    media_type: Literal["novel", "visual_novel", "manga", "other"] = "novel"
    total_chars: Positive | None = None
    status: Literal["reading", "finished", "dropped"] = "reading"


class LogInput(Input):
    media_id: Annotated[int, Field(strict=True, gt=0)]
    date: Date
    chars: Positive
    minutes: Annotated[int, Field(strict=True, gt=0, le=1440)] | None = None

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        if value < Date(1900, 1, 1):
            raise ValueError("Reading dates must be on or after 1900-01-01")
        return value


class MediaSnapshot(MediaInput):
    cover_url: str | None = Field(default=None, max_length=2048)

    @field_validator("cover_url")
    @classmethod
    def valid_cover(cls, value):
        if value is not None:
            url = urlsplit(value)
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("Cover must be a public HTTPS image URL")
        return value

    jiten_id: Annotated[int, Field(strict=True, gt=0)] | None = None
    difficulty: Annotated[float, Field(allow_inf_nan=False)] | None = None
    unique_words: Annotated[int, Field(strict=True, ge=0)] | None = None
    unique_kanji: Annotated[int, Field(strict=True, ge=0)] | None = None


class CountInput(Input):
    text: str = Field(max_length=500_000)
