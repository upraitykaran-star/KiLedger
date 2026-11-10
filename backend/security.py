import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()
_attempts: dict[str, deque[float]] = defaultdict(deque)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def check_login_rate(request: Request, settings) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _attempts[key]
    while bucket and now - bucket[0] > settings.rate_window_seconds:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit:
        raise HTTPException(429, "Too many login attempts. Try again shortly.")
    bucket.append(now)


def issue_session(db, response: Response, user_id: str, business_id: str, settings) -> str:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    expires = utcnow() + timedelta(days=settings.session_days)
    db.sessions.insert_one({"token_hash": hash_token(token), "csrf_hash": hash_token(csrf), "user_id": user_id,
                            "business_id": business_id, "expires_at": expires, "created_at": utcnow()})
    response.set_cookie(settings.session_cookie, token, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=settings.session_days * 86400, path="/")
    return csrf


def require_session(request: Request, response: Response, db, settings, csrf_required: bool = True) -> dict:
    token = request.cookies.get(settings.session_cookie)
    session = db.sessions.find_one({"token_hash": hash_token(token)}) if token else None
    if not session or session["expires_at"] <= utcnow():
        raise HTTPException(401, "Sign in to continue.")
    if csrf_required and request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(hash_token(supplied), session["csrf_hash"]):
            raise HTTPException(403, "Request verification failed. Refresh your session.")
    member = db.memberships.find_one({"business_id": session["business_id"], "user_id": session["user_id"]})
    user = db.users.find_one({"_id": session["user_id"], "disabled": {"$ne": True}})
    if not member or not user:
        raise HTTPException(403, "Business access is no longer available.")
    return {"user_id": user["_id"], "email": user["email"], "name": user["name"],
            "business_id": member["business_id"], "role": member["role"], "csrf_token": None,
            "session_hash": hash_token(token)}
