"""Signed-token auth and bcrypt password hashing."""
import base64
import json
import os
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

SECRET = os.environ.get("INTENTOS_SECRET", "change-me-in-production")
_bearer = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def sign_token(payload: dict, ttl_seconds: int = 86400) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    encoded = _b64(json.dumps(body, separators=(",", ":")).encode())
    import hashlib
    import hmac
    sig = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{sig}"


def decode_token(token: str) -> dict | None:
    try:
        encoded, sig = token.split(".", 1)
        expected = hmac.new(SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(encoded).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def require_auth(roles: list[str] | None = None):
    def _dep(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
        if credentials is None:
            raise HTTPException(status_code=401, detail="missing bearer token")
        payload = decode_token(credentials.credentials)
        if payload is None:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        if roles and payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="insufficient role")
        return payload
    return _dep
