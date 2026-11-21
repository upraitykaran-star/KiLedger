import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import select

from .database import Business, Membership, SessionRecord, User

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


def issue_session(session, response: Response, user_id: str, business_id: str, settings) -> str:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = utcnow()
    session.add(SessionRecord(token_hash=hash_token(token), csrf_hash=hash_token(csrf), user_id=user_id,
                              business_id=business_id, expires_at=now + timedelta(days=settings.session_days), created_at=now))
    session.commit()
    response.set_cookie(settings.session_cookie, token, httponly=True, secure=settings.cookie_secure,
                        samesite="lax", max_age=settings.session_days * 86400, path="/")
    return csrf


def require_session(request: Request, response: Response, session, settings, csrf_required: bool = True) -> dict:
    token = request.cookies.get(settings.session_cookie)
    record = session.get(SessionRecord, hash_token(token)) if token else None
    expires_at = record.expires_at if record else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not record or expires_at <= utcnow():
        raise HTTPException(401, "Sign in to continue.")
    if csrf_required and request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(hash_token(supplied), record.csrf_hash):
            raise HTTPException(403, "Request verification failed. Refresh your session.")
    member = session.scalar(select(Membership).where(Membership.business_id == record.business_id, Membership.user_id == record.user_id))
    user = session.get(User, record.user_id)
    business = session.get(Business, record.business_id)
    if not member or not user or user.disabled or not business:
        raise HTTPException(403, "Business access is no longer available.")
    return {"user_id": user.id, "email": user.email, "name": user.name, "business_id": member.business_id,
            "role": member.role, "csrf_token": None, "session_hash": record.token_hash}
