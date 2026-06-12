"""Append-only TSV response storage."""

from __future__ import annotations

import csv
import fcntl
import threading
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ResponseStore:
    """Store one immutable response per verified email and question."""

    FIELDS = [
        "timestamp",
        "email",
        "name",
        "question",
        "answer",
        "ip",
        "user_agent",
        "token_sub",
        "email_verified",
        "google_sub",
    ]
    _locks: defaultdict[Path, threading.Lock] = defaultdict(threading.Lock)

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
        self._cache_signature: tuple[int, int] | None = None
        self._answers_cache: dict[str, dict[str, str]] = {}

    def answers_for(self, email: str) -> dict[str, str]:
        if not self.path.exists():
            return {}
        with self._locks[self.path], self.path.open(newline="") as file:
            fcntl.flock(file, fcntl.LOCK_SH)
            stat = self.path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
            if signature == self._cache_signature:
                fcntl.flock(file, fcntl.LOCK_UN)
                return dict(self._answers_cache.get(email.lower(), {}))
            answers: defaultdict[str, dict[str, str]] = defaultdict(dict)
            for row in csv.DictReader(file, delimiter="\t"):
                answers[row.get("email", "").lower()][row["question"]] = row["answer"]
            fcntl.flock(file, fcntl.LOCK_UN)
            self._answers_cache = dict(answers)
            self._cache_signature = signature
        return dict(self._answers_cache.get(email.lower(), {}))

    def submit(
        self,
        identity: dict[str, Any],
        question: str,
        answer: str,
        ip: str,
        user_agent: str,
    ) -> bool:
        """Atomically append an answer, returning false when it already exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        email = str(identity["email"]).lower()
        with self._locks[self.path], self.path.open("a+", newline="") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            file.seek(0)
            if any(
                row.get("email", "").lower() == email and row.get("question") == question
                for row in csv.DictReader(file, delimiter="\t")
            ):
                fcntl.flock(file, fcntl.LOCK_UN)
                return False

            file.seek(0, 2)
            writer = csv.DictWriter(
                file, fieldnames=self.FIELDS, delimiter="\t", lineterminator="\n"
            )
            if file.tell() == 0:
                writer.writeheader()
            sub = str(identity["sub"])
            writer.writerow(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "email": email,
                    "name": identity.get("name", ""),
                    "question": question,
                    "answer": answer,
                    "ip": ip,
                    "user_agent": user_agent,
                    "token_sub": sub,
                    "email_verified": str(bool(identity["email_verified"])).lower(),
                    "google_sub": sub,
                }
            )
            file.flush()
            self._cache_signature = None
            fcntl.flock(file, fcntl.LOCK_UN)
        return True
