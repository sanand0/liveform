"""App fixture used by the real-browser smoke test."""

import os
from pathlib import Path

from liveform.server import create_app


class BrowserVerifier:
    def verify(self, token: str) -> dict:
        if token != "student-token":
            raise ValueError("Invalid token")
        return {
            "email": "student@study.iitm.ac.in",
            "email_verified": True,
            "name": "Browser Student",
            "sub": "browser-student",
        }


app = create_app(
    Path(os.environ["LIVEFORM_BROWSER_FORMS"]),
    "browser-client",
    "http://127.0.0.1:8765",
    verifier=BrowserVerifier(),
)
