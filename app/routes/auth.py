import secrets

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.auth import (
    DB,
    CurrentUser,
    digest,
    dummy_hash,
    hasher,
    login,
    session_key,
    throttle,
    user_data,
    verify,
)
from app.config import settings
from app.models import ApiToken, LoginSession, User
from app.schemas import Credentials, Preferences

router = APIRouter(prefix="/api")


@router.post("/register", status_code=201)
def register(data: Credentials, request: Request, response: Response, db: DB):
    throttle(request)
    mode = settings().registration_mode
    if mode == "closed":
        raise HTTPException(403, "Registration is closed")
    if db.bind.dialect.name == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
    if mode == "first_user" and db.scalar(select(User.id).limit(1)):
        raise HTTPException(403, "Registration is closed; the first account already exists")
    user = User(username=data.username.lower(), password_hash=hasher.hash(data.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username is already taken")
    login(db, user, response, request)
    return user_data(user)


@router.post("/login")
def sign_in(data: Credentials, request: Request, response: Response, db: DB):
    throttle(request)
    user = db.scalar(select(User).where(User.username == data.username.lower()))
    valid = verify(data.password, user.password_hash if user else dummy_hash)
    if not user or not valid:
        raise HTTPException(401, "Incorrect username or password")
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(data.password)
    login(db, user, response, request)
    return user_data(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: DB):
    key = session_key(request)
    if key:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == key))
        db.commit()
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser):
    return user_data(user)


@router.patch("/me")
def preferences(data: Preferences, user: CurrentUser, db: DB):
    for key, value in data.model_dump().items():
        setattr(user, key, value)
    db.commit()
    return user_data(user)


@router.post("/token")
def create_token(user: CurrentUser, db: DB):
    db.execute(delete(ApiToken).where(ApiToken.user_id == user.id))
    raw = "rs_" + secrets.token_urlsafe(32)
    db.add(ApiToken(user_id=user.id, token_hash=digest(raw)))
    db.commit()
    return {"token": raw}


@router.delete("/token")
def revoke_token(user: CurrentUser, db: DB):
    db.execute(delete(ApiToken).where(ApiToken.user_id == user.id))
    db.commit()
    return {"ok": True}
