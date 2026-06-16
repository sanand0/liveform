"""Load and validate live form configuration."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import nh3
import yaml
from markdown_it import MarkdownIt

logger = logging.getLogger("liveform.config")

FIELDS = {"text", "textarea", "single_choice", "multi_choice"}
INPUT_TYPES = {"date", "datetime-local", "email", "number", "tel", "text", "time", "url"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": True})


def render_markdown(value: Any) -> str:
    """Render untrusted Markdown as sanitized HTML."""
    return nh3.clean(MARKDOWN.render(str(value or "")))


def render_plain_text(value: Any) -> str:
    """Render Markdown-ish labels as text for browser chrome and metadata."""
    html_text = render_markdown(value)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(html_text))).strip()


@dataclass(frozen=True)
class Question:
    id: str
    field: str
    question_html: str
    description_html: str = ""
    choices: tuple[str, ...] = ()
    type: str = "text"
    minlength: int | None = None
    maxlength: int | None = None
    pattern: str | None = None

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data["choices"] = list(self.choices)
        return {key: value for key, value in data.items() if value not in (None, "", [], ())}


@dataclass(frozen=True)
class Form:
    slug: str
    title_text: str
    title_html: str
    description_html: str
    questions: tuple[Question, ...]
    allowed_domains: frozenset[str] = field(default_factory=frozenset)
    allowed_emails: frozenset[str] = field(default_factory=frozenset)
    version: str = ""

    def question(self, question_id: str) -> Question | None:
        return next((question for question in self.questions if question.id == question_id), None)

    def public(self) -> dict[str, Any]:
        return {
            "title_text": self.title_text,
            "title_html": self.title_html,
            "description_html": self.description_html,
            "questions": [question.public() for question in self.questions],
            "version": self.version,
        }


class ConfigError(ValueError):
    """The form configuration cannot be loaded."""


class AuthConfigError(ConfigError):
    """Authorization configuration is invalid and must fail closed."""


class FormRegistry:
    """Discover forms and retain the last valid configuration while files are edited."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self._cache: dict[str, tuple[tuple[int, int], Form]] = {}
        self._failed_signatures: dict[str, tuple[int, int]] = {}
        self._blocked_errors: dict[str, tuple[tuple[int, int], ConfigError]] = {}
        self._lock = threading.RLock()

    def slugs(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(path.parent.name for path in self.root.glob("*/form.yaml") if path.is_file())

    def get(self, slug: str) -> Form:
        with self._lock:
            path = self._config_path(slug)
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            cached = self._cache.get(slug)
            blocked = self._blocked_errors.get(slug)
            if blocked and blocked[0] == signature:
                raise blocked[1]
            if cached and (
                cached[0] == signature or self._failed_signatures.get(slug) == signature
            ):
                return cached[1]

            try:
                form = self._load(slug, path)
            except AuthConfigError as error:
                blocked_error = ConfigError(
                    f"Invalid authorization configuration for {slug}: {error}"
                )
                self._blocked_errors[slug] = (signature, blocked_error)
                logger.error(
                    "Blocking %s until authorization configuration is valid: %s", slug, error
                )
                raise blocked_error from error
            except Exception as error:
                if not cached:
                    raise ConfigError(f"Invalid configuration for {slug}: {error}") from error
                self._failed_signatures[slug] = signature
                logger.warning("Keeping previous valid configuration for %s: %s", slug, error)
                return cached[1]

            self._cache[slug] = (signature, form)
            self._failed_signatures.pop(slug, None)
            self._blocked_errors.pop(slug, None)
            return form

    def _config_path(self, slug: str) -> Path:
        if not ID_PATTERN.fullmatch(slug):
            raise KeyError(slug)
        path = self.root / slug / "form.yaml"
        if not path.is_file():
            raise KeyError(slug)
        return path

    def _load(self, slug: str, path: Path) -> Form:
        raw = yaml.safe_load(path.read_text())
        if not isinstance(raw, dict):
            raise ConfigError("form.yaml must contain a mapping")
        questions_raw = raw.get("questions", [])
        if not isinstance(questions_raw, list):
            raise ConfigError("questions must be a list")

        types_path = path.parent / ".liveform-types.json"
        types = self._read_types(types_path)
        seen: set[str] = set()
        questions: list[Question] = []
        for index, item in enumerate(questions_raw, 1):
            question = self._parse_question(slug, index, item, seen, types)
            if question:
                seen.add(question.id)
                if not bool(item.get("hidden", False)):
                    questions.append(question)
        self._write_types(types_path, types)

        allowed_domains, allowed_emails = self._auth_rules(raw.get("auth"))
        title = raw.get("title", slug)
        payload = {
            "title_text": render_plain_text(title),
            "title_html": render_markdown(title),
            "description_html": render_markdown(raw.get("description", "")),
            "questions": [question.public() for question in questions],
        }
        version = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return Form(
            slug=slug,
            title_text=payload["title_text"],
            title_html=payload["title_html"],
            description_html=payload["description_html"],
            questions=tuple(questions),
            allowed_domains=frozenset(allowed_domains),
            allowed_emails=frozenset(allowed_emails),
            version=version,
        )

    def _parse_question(
        self,
        slug: str,
        index: int,
        item: Any,
        seen: set[str],
        types: dict[str, str],
    ) -> Question | None:
        def skip(reason: str) -> None:
            logger.warning("Skipping %s question %d: %s", slug, index, reason)

        if not isinstance(item, dict):
            skip("question must be a mapping")
            return None
        question_id = item.get("id")
        if not isinstance(question_id, str) or not ID_PATTERN.fullmatch(question_id):
            skip("id is missing or invalid")
            return None
        if question_id in seen:
            skip(f"duplicate id {question_id!r}")
            return None
        field_name = item.get("field", "single_choice" if "choices" in item else "text")
        if field_name not in FIELDS:
            skip(f"unsupported field {field_name!r}")
            return None
        original_field = types.get(question_id)
        if original_field and original_field != field_name:
            skip(f"{question_id!r} cannot change field from {original_field!r} to {field_name!r}")
            return None
        if not item.get("question"):
            skip("question text is required")
            return None

        choices: tuple[str, ...] = ()
        if field_name in {"single_choice", "multi_choice"}:
            raw_choices = item.get("choices")
            if (
                not isinstance(raw_choices, list)
                or not raw_choices
                or any(not isinstance(choice, str) or not choice for choice in raw_choices)
                or len(set(raw_choices)) != len(raw_choices)
            ):
                skip("choices must be a non-empty list of unique strings")
                return None
            choices = tuple(raw_choices)

        input_type = item.get("type", "text")
        if field_name == "text" and input_type not in INPUT_TYPES:
            skip(f"unsupported input type {input_type!r}")
            return None
        minlength = self._optional_nonnegative_int(item.get("minlength"))
        maxlength = self._optional_nonnegative_int(item.get("maxlength"))
        if item.get("minlength") is not None and minlength is None:
            skip("minlength must be a non-negative integer")
            return None
        if item.get("maxlength") is not None and maxlength is None:
            skip("maxlength must be a non-negative integer")
            return None
        if minlength is not None and maxlength is not None and minlength > maxlength:
            skip("minlength cannot exceed maxlength")
            return None
        pattern = item.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                skip("pattern must be a string")
                return None
            try:
                re.compile(pattern)
            except re.error:
                skip("pattern is not a valid regular expression")
                return None

        types.setdefault(question_id, field_name)
        return Question(
            id=question_id,
            field=field_name,
            question_html=render_markdown(item["question"]),
            description_html=render_markdown(item.get("description", "")),
            choices=choices,
            type=input_type if field_name == "text" else "text",
            minlength=minlength,
            maxlength=maxlength,
            pattern=pattern,
        )

    @staticmethod
    def _optional_nonnegative_int(value: Any) -> int | None:
        return (
            value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        )

    @staticmethod
    def _auth_rules(auth: Any) -> tuple[set[str], set[str]]:
        if auth is None:
            return set(), set()
        if not isinstance(auth, dict):
            raise AuthConfigError("auth must be a mapping")

        def values(key: str) -> set[str]:
            raw = auth.get(key, [])
            if not isinstance(raw, list) or any(
                not isinstance(item, str) or not item.strip() for item in raw
            ):
                raise AuthConfigError(f"auth.{key} must be a list of non-empty strings")
            return {item.strip().lower() for item in raw}

        domains = values("allowed_domains")
        emails = values("allowed_emails")
        if any("@" in domain or "." not in domain for domain in domains):
            raise AuthConfigError("auth.allowed_domains contains an invalid domain")
        if any(email.count("@") != 1 for email in emails):
            raise AuthConfigError("auth.allowed_emails contains an invalid email")
        return domains, emails

    @staticmethod
    def _read_types(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text())
            return {
                key: value
                for key, value in data.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        except (OSError, ValueError, AttributeError):
            logger.warning("Ignoring invalid question type state at %s", path)
            return {}

    @staticmethod
    def _write_types(path: Path, types: dict[str, str]) -> None:
        content = json.dumps(types, indent=2, sort_keys=True) + "\n"
        if path.exists() and path.read_text() == content:
            return
        temporary = path.with_suffix(".tmp")
        temporary.write_text(content)
        temporary.replace(path)
