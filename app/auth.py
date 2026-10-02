import hashlib
import secrets
import threading
import time
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cachetools import TTLCache
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import ApiToken, LoginSession, User

DB = Annotated[Session, Depends(get_db)]
hasher = PasswordHasher()
serializer = URLSafeTimedSerializer(settings().secret_key, salt="reading-site-session")
SESSION_AGE = 60 * 60 * 24 * 14
dummy_hash = hasher.hash(secrets.token_urlsafe(24))
attempts = TTLCache(maxsize=10000, ttl=900)
attempt_lock = threading.Lock()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def throttle(request: Request):
    # One worker is required for this in-process limiter and the Jiten cache.
    key = request.client.host if request.client else "unknown"
    with attempt_lock:
        count = attempts.get(key, 0)
        if count >= 30:
            raise HTTPException(429, "Too many login attempts; try again in 15 minutes", headers={"Retry-After": "900"})
        attempts[key] = count + 1


def verify(password, password_hash):
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def session_key(request):
    try:
        raw = serializer.loads(request.cookies.get("session", ""), max_age=SESSION_AGE)
        return digest(raw) if isinstance(raw, str) else None
    except BadSignature:
        return None


def current_user(request: Request, db: DB):
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        token = db.scalar(select(ApiToken).where(ApiToken.token_hash == digest(authorization[7:])))
        uid = token.user_id if token else None
    else:
        key = session_key(request)
        session = db.get(LoginSession, key) if key else None
        uid = session.user_id if session and session.expires > int(time.time()) else None
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Please sign in")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def login(db, user, response: Response, request: Request):
    old = session_key(request)
    if old:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == old))
    db.execute(delete(LoginSession).where(LoginSession.expires <= int(time.time())))
    raw = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=digest(raw), user_id=user.id, expires=int(time.time()) + SESSION_AGE))
    db.commit()
    response.set_cookie("session", serializer.dumps(raw), max_age=SESSION_AGE,
                        httponly=True, secure=settings().cookie_secure, samesite="lax", path="/")


def user_data(user):
    return {k: getattr(user, k) for k in (
        "id", "username", "timezone", "daily_goal", "weekly_goal", "monthly_goal", "public_profile"
    )}
