"""Validate and persist file upload answers."""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from liveform.config import Question

MIME_EXTENSIONS = {
    "application/gzip": ".gz",
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "text/csv": ".csv",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/plain": ".txt",
}


async def save_upload(
    root: Path, question: Question, email: str, upload: UploadFile
) -> tuple[str, bool]:
    """Validate and save an uploaded answer, returning relative path and preexistence."""
    content_type = upload.content_type.split(";", 1)[0].strip().lower() if upload.content_type else ""
    original_extension = safe_extension(upload.filename or "")
    inferred_extension = MIME_EXTENSIONS.get(content_type) or mimetypes.guess_extension(content_type)
    extension = safe_extension(inferred_extension or "") or original_extension or ".bin"
    if not accepted_upload(question.accept, content_type, original_extension, extension):
        raise HTTPException(422, "File type is not accepted")
    data = await upload.read((question.max_size or 0) + 1)
    if question.max_size is None or len(data) > question.max_size:
        raise HTTPException(413, "File is too large")
    digest = hashlib.sha256(data).hexdigest()[:12]
    relative = f"uploads/{question.id}--{email_slug(email)}--{digest}{extension}"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if not existed:
        path.write_bytes(data)
    return relative, existed


def accepted_upload(
    accept: tuple[str, ...], content_type: str, original_extension: str, saved_extension: str
) -> bool:
    """Match the browser accept syntax the config allows."""
    if not accept:
        return True
    content_main = content_type.split("/", 1)[0] if "/" in content_type else ""
    extensions = {original_extension, saved_extension} - {""}
    for item in accept:
        if item.startswith(".") and item in extensions:
            return True
        if item.endswith("/*") and content_main and item[:-2] == content_main:
            return True
        if "/" in item and item == content_type:
            return True
    return False


def safe_extension(filename: str) -> str:
    """Return a conservative single extension, including the dot."""
    value = filename.lower()
    extension = value if value.startswith(".") and "/" not in value else Path(value).suffix
    return extension if re.fullmatch(r"\.[a-z0-9][a-z0-9_-]{0,31}", extension) else ""


def email_slug(email: str) -> str:
    """Make an email address safe for a flat upload filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")
    return slug or "unknown"
