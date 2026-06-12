"""FastAPI application for liveform."""

from __future__ import annotations

import html
import io
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import segno
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from liveform.assets import CSS, JS, PAGE
from liveform.auth import GoogleTokenVerifier, is_authorized, normalize_identity
from liveform.config import ConfigError, Form, FormRegistry, Question
from liveform.store import ResponseStore

MAX_REQUEST_BYTES = 1_000_000
MAX_TEXT_ANSWER_LENGTH = 100_000


class AnswerRequest(BaseModel):
    question: str
    answer: Any


def create_app(
    forms_dir: Path | str,
    google_client_id: str,
    public_url: str,
    *,
    verifier: Any | None = None,
) -> FastAPI:
    """Create an app serving every direct child form directory."""
    # Kept for API compatibility; QR targets now follow the origin used by each visitor.
    del public_url
    root = Path(forms_dir).resolve()
    registry = FormRegistry(root)
    token_verifier = verifier or GoogleTokenVerifier(google_client_id)
    app = FastAPI(
        title="liveform",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    def get_form(slug: str) -> Form:
        try:
            return registry.get(slug)
        except (KeyError, FileNotFoundError):
            raise HTTPException(404, "Form not found") from None
        except (ConfigError, OSError) as error:
            raise HTTPException(503, str(error)) from error

    def authenticate(form: Form, authorization: str | None) -> dict[str, Any]:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Google sign-in required")
        try:
            identity = normalize_identity(
                token_verifier.verify(authorization.removeprefix("Bearer "))
            )
        except Exception as error:
            raise HTTPException(401, "Invalid or expired Google sign-in") from error
        if not is_authorized(form, identity):
            raise HTTPException(403, "This Google account is not allowed to respond")
        return identity

    @lru_cache
    def store(slug: str) -> ResponseStore:
        return ResponseStore(root / slug / "responses.tsv")

    @lru_cache
    def qr_svg(target: str) -> bytes:
        code = segno.make(target, error="m")
        output = io.BytesIO()
        code.save(output, kind="svg", scale=4, border=1, xmldecl=False)
        return output.getvalue()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
            response = Response("Request too large", status_code=413, media_type="text/plain")
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://accounts.google.com; "
            "frame-src https://accounts.google.com; connect-src 'self' https://accounts.google.com; "
            "img-src 'self' data:; style-src 'self' 'unsafe-inline' https://accounts.google.com; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/{slug}", response_class=HTMLResponse)
    @app.get("/{slug}/", response_class=HTMLResponse)
    @app.get("/{slug}/index.html", response_class=HTMLResponse)
    def page(slug: str) -> Response:
        get_form(slug)
        content = PAGE.format(
            slug=html.escape(slug, quote=True),
            client_id=html.escape(google_client_id, quote=True),
        )
        return HTMLResponse(content, headers={"Cache-Control": "no-cache"})

    @app.get("/{slug}/app.css")
    def css(slug: str) -> Response:
        get_form(slug)
        return Response(CSS, media_type="text/css", headers={"Cache-Control": "public, max-age=60"})

    @app.get("/{slug}/app.js")
    def javascript(slug: str) -> Response:
        get_form(slug)
        return Response(
            JS,
            media_type="text/javascript",
            headers={"Cache-Control": "public, max-age=60"},
        )

    @app.get("/{slug}/qr.svg")
    def qr(slug: str, request: Request) -> Response:
        get_form(slug)
        forwarded_scheme = request.headers.get("X-Forwarded-Proto", "").split(",", 1)[0].strip()
        scheme = forwarded_scheme if forwarded_scheme in {"http", "https"} else request.url.scheme
        target = f"{scheme}://{request.url.netloc}/{slug}/"
        return Response(
            qr_svg(target),
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "no-store",
                "X-Liveform-QR-Target": target,
            },
        )

    @app.get("/{slug}/version")
    def version(slug: str, if_none_match: str | None = Header(None)) -> Response:
        form = get_form(slug)
        etag = f'"{form.version}"'
        headers = {"ETag": etag, "Cache-Control": "no-cache"}
        if if_none_match == etag:
            return Response(status_code=304, headers=headers)
        return PlainTextResponse(form.version, headers=headers)

    @app.get("/{slug}/state")
    def state(slug: str, authorization: str | None = Header(None)) -> Response:
        form = get_form(slug)
        identity = authenticate(form, authorization)
        payload = {
            **form.public(),
            "identity": {"email": identity["email"], "name": identity["name"]},
            "answers": store(slug).answers_for(identity["email"]),
        }
        return Response(
            json.dumps(payload, separators=(",", ":")),
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/{slug}/answers", status_code=201)
    def submit(
        slug: str,
        submission: AnswerRequest,
        request: Request,
        authorization: str | None = Header(None),
    ) -> Response:
        form = get_form(slug)
        identity = authenticate(form, authorization)
        question = form.question(submission.question)
        if not question:
            raise HTTPException(404, "Question not found or not available")
        answer = validate_answer(question, submission.answer)
        ip = request.headers.get("CF-Connecting-IP") or (
            request.client.host if request.client else ""
        )
        created = store(slug).submit(
            identity,
            question.id,
            answer,
            ip,
            request.headers.get("User-Agent", ""),
        )
        if not created:
            raise HTTPException(409, "This question has already been submitted")
        return Response(
            json.dumps({"answer": answer}, separators=(",", ":")),
            status_code=201,
            media_type="application/json",
            headers={"Cache-Control": "no-store"},
        )

    return app


def validate_answer(question: Question, value: Any) -> str:
    """Validate and serialize an answer using the current question contract."""
    if question.field in {"text", "textarea"}:
        if not isinstance(value, str) or not value:
            raise HTTPException(422, "Answer must be a non-empty string")
        if len(value) > MAX_TEXT_ANSWER_LENGTH:
            raise HTTPException(422, f"Answer cannot exceed {MAX_TEXT_ANSWER_LENGTH} characters")
        if question.minlength is not None and len(value) < question.minlength:
            raise HTTPException(
                422, f"Answer must contain at least {question.minlength} characters"
            )
        if question.maxlength is not None and len(value) > question.maxlength:
            raise HTTPException(422, f"Answer must contain at most {question.maxlength} characters")
        if question.pattern and not re.fullmatch(question.pattern, value):
            raise HTTPException(422, "Answer does not match the required pattern")
        return value
    if question.field == "single_choice":
        if not isinstance(value, str) or value not in question.choices:
            raise HTTPException(422, "Answer must be one of the configured choices")
        return value
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or item not in question.choices for item in value)
        or len(set(value)) != len(value)
    ):
        raise HTTPException(422, "Answer must be a non-empty list of unique configured choices")
    return json.dumps(value, separators=(",", ":"))
