from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import DB
from app.config import settings
from app.models import User
from app.routes import auth, logs, media, stats, transfer
from app.stats import summary, today_for

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Reading Site", version="0.1.0")


class BodyLimit:
    """Bound JSON bodies, including chunked requests, before parsers allocate memory."""
    def __init__(self, app, limit=5 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PATCH", "PUT"):
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.limit:
                response = JSONResponse({"detail": "Request is larger than 5 MB"}, status_code=413)
                return await response(scope, receive, send)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


app.add_middleware(BodyLimit)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[urlsplit(settings().app_origin).hostname, "localhost", "127.0.0.1", "testserver"])


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        bearer = request.headers.get("authorization", "").startswith("Bearer ")
        if origin and origin != settings().app_origin:
            return JSONResponse({"detail": "Origin is not allowed"}, status_code=403)
        if not bearer and request.headers.get("x-reading-site") != "1":
            return JSONResponse({"detail": "Missing X-Reading-Site header"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.startswith(("/api/", "/profile/")):
        response.headers["Cache-Control"] = "no-store"
    if settings().cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse({"detail": "This change conflicts with an existing record"}, status_code=409)


for router in (auth.router, logs.router, media.router, stats.router, transfer.router):
    app.include_router(router)


@app.get("/api/public/{username}")
def public_profile(username: str, db: DB):
    user = db.scalar(select(User).where(User.username == username.lower(), User.public_profile.is_(True)))
    if not user:
        raise HTTPException(404, "Profile not found")
    values = summary(stats.user_logs(db, user), user, today_for(user))
    return {"username": user.username, **{key: values[key] for key in ("total_chars", "reading_days", "reading_streak", "goal_streak")}}


@app.get("/health")
def health(db: DB):
    db.execute(select(User.id).limit(1))
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/profile/{username}")
def profile_page(username: str):
    return FileResponse(ROOT / "static" / "profile.html")


app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
