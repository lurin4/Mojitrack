from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str]
    timezone: Mapped[str] = mapped_column(default="Europe/London")
    daily_goal: Mapped[int] = mapped_column(default=1000)
    weekly_goal: Mapped[int] = mapped_column(default=7000)
    monthly_goal: Mapped[int] = mapped_column(default=30000)
    public_profile: Mapped[bool] = mapped_column(default=False)


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "users.id", ondelete="CASCADE"), index=True)
    expires: Mapped[int]


class ApiToken(Base):
    __tablename__ = "api_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "users.id", ondelete="CASCADE"), unique=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    jiten_id: Mapped[int | None]
    cover_url: Mapped[str | None]
    media_type: Mapped[str] = mapped_column(default="novel")
    total_chars: Mapped[int | None]
    difficulty: Mapped[float | None]
    unique_words: Mapped[int | None]
    unique_kanji: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="reading")
    __table_args__ = (
        UniqueConstraint("user_id", "jiten_id"),
        CheckConstraint("status IN ('reading', 'finished', 'dropped')"),
        CheckConstraint("total_chars IS NULL OR total_chars > 0"),
    )


class ReadingLog(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"))
    date: Mapped[date]
    chars: Mapped[int]
    minutes: Mapped[int | None]
    __table_args__ = (
        Index("ix_logs_user_date", "user_id", "date"),
        CheckConstraint("chars > 0"),
        CheckConstraint("minutes IS NULL OR minutes > 0"),
    )


class ImportReceipt(Base):
    __tablename__ = "imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    digest: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("user_id", "digest"),)
