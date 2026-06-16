"""Google ID token verification and form authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from liveform.config import Form

SESSION_LIFETIME_SECONDS = 24 * 60 * 60


class GoogleTokenVerifier:
    """Verify Google ID tokens and cache valid claims until token expiry."""

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.request = Request()
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def verify(self, token: str) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            cached = self._cache.get(token)
            if cached and float(cached.get("exp", 0)) > now + 30:
                return cached
        claims = id_token.verify_oauth2_token(token, self.request, self.client_id)
        with self._lock:
            self._cache = {
                key: value
                for key, value in self._cache.items()
                if float(value.get("exp", 0)) > now + 30
            }
            self._cache[token] = claims
        return claims


class SessionTokenSigner:
    """Create and verify local Liveform sessions after Google sign-in."""

    def __init__(self, secret: bytes):
        self.secret = secret

    def create(self, identity: dict[str, Any], now: float | None = None) -> tuple[str, int]:
        expires_at = int((now or time.time()) + SESSION_LIFETIME_SECONDS)
        payload = {
            "email": identity["email"],
            "name": identity["name"],
            "sub": identity["sub"],
            "email_verified": identity["email_verified"],
            "exp": expires_at,
        }
        token = self._encode(payload)
        return token, expires_at

    def verify(self, token: str) -> dict[str, Any]:
        payload_segment, signature = token.split(".", 1)
        expected = self._signature(payload_segment)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid session signature")
        payload = json.loads(self._decode(payload_segment))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Session expired")
        return normalize_identity(payload)

    def _encode(self, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        payload_segment = self._b64encode(data)
        return f"{payload_segment}.{self._signature(payload_segment)}"

    def _signature(self, payload_segment: str) -> str:
        digest = hmac.new(self.secret, payload_segment.encode(), hashlib.sha256).digest()
        return self._b64encode(digest)

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def _decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


def normalize_identity(claims: dict[str, Any]) -> dict[str, Any]:
    email = str(claims.get("email", "")).strip().lower()
    sub = str(claims.get("sub", "")).strip()
    verified = claims.get("email_verified") is True or claims.get("email_verified") == "true"
    if not email or not sub:
        raise ValueError("Google token is missing email or subject")
    return {
        "email": email,
        "name": str(claims.get("name", "")).strip(),
        "sub": sub,
        "email_verified": verified,
    }


def is_authorized(form: Form, identity: dict[str, Any]) -> bool:
    if not identity["email_verified"]:
        return False
    if not form.allowed_domains and not form.allowed_emails:
        return True
    email = identity["email"]
    domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    return email in form.allowed_emails or domain in form.allowed_domains
