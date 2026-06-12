"""Google ID token verification and form authorization."""

from __future__ import annotations

import threading
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2 import id_token

from liveform.config import Form


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
