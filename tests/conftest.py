from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liveform.server import create_app


FORM_YAML = """\
title: AI Workshop
description: "**Welcome.**"
auth:
  allowed_domains: [example.edu]
  allowed_emails: [guest@gmail.com]
questions:
  - id: link
    field: text
    question: Submit your **link**
    description: Use a public URL.
    type: url
    minlength: 10
    maxlength: 200
    pattern: "https?://.+"
  - id: useful
    field: single_choice
    question: How useful was this?
    choices: [Low, High]
  - id: tools
    field: multi_choice
    question: Which tools?
    choices: [ChatGPT, Gemini, Codex]
  - id: notes
    field: textarea
    question: Notes
  - id: hidden
    field: text
    question: Not yet
    hidden: true
"""


class FakeVerifier:
    def __init__(self) -> None:
        self.tokens = {
            "student-token": {
                "email": "student@example.edu",
                "email_verified": True,
                "name": "Student",
                "sub": "student-sub",
            },
            "guest-token": {
                "email": "guest@gmail.com",
                "email_verified": True,
                "name": "Guest",
                "sub": "guest-sub",
            },
            "other-token": {
                "email": "other@gmail.com",
                "email_verified": True,
                "name": "Other",
                "sub": "other-sub",
            },
            "unverified-token": {
                "email": "student@example.edu",
                "email_verified": False,
                "name": "Unverified",
                "sub": "unverified-sub",
            },
        }

    def verify(self, token: str) -> dict:
        if token not in self.tokens:
            raise ValueError("Invalid token")
        return self.tokens[token]


@pytest.fixture
def forms_dir(tmp_path: Path) -> Path:
    form_dir = tmp_path / "workshop"
    form_dir.mkdir()
    (form_dir / "form.yaml").write_text(FORM_YAML)
    return tmp_path


@pytest.fixture
def verifier() -> FakeVerifier:
    return FakeVerifier()


@pytest.fixture
def client(forms_dir: Path, verifier: FakeVerifier) -> TestClient:
    app = create_app(forms_dir, "client-id", "https://forms.example", verifier=verifier)
    return TestClient(app)


@pytest.fixture
def auth() -> dict[str, str]:
    return {"Authorization": "Bearer student-token"}
