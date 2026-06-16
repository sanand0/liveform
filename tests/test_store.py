import csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from liveform.store import ResponseStore


IDENTITY = {
    "email": "student@example.edu",
    "name": "Student",
    "sub": "google-123",
    "email_verified": True,
}


def test_appends_expected_tsv_record_and_reads_answered(tmp_path: Path) -> None:
    store = ResponseStore(tmp_path / "responses.tsv")

    assert store.submit(IDENTITY, "q1", "answer", "203.0.113.2", "Browser") is True
    assert store.answers_for("student@example.edu") == {"q1": "answer"}

    with (tmp_path / "responses.tsv").open(newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    assert list(rows[0]) == ResponseStore.FIELDS
    assert rows[0]["timestamp"].endswith("+00:00")
    assert rows[0]["email"] == "student@example.edu"
    assert rows[0]["token_sub"] == "google-123"
    assert rows[0]["google_sub"] == "google-123"
    assert rows[0]["email_verified"] == "true"
    assert rows[0]["ip"] == "203.0.113.2"


def test_duplicate_email_question_is_rejected_without_append(tmp_path: Path) -> None:
    store = ResponseStore(tmp_path / "responses.tsv")

    assert store.submit(IDENTITY, "q1", "first", "", "") is True
    assert store.submit(IDENTITY, "q1", "second", "", "") is False

    assert store.answers_for(IDENTITY["email"]) == {"q1": "first"}
    assert store.answer_counts() == {"q1": 1}


def test_concurrent_duplicate_submissions_append_once(tmp_path: Path) -> None:
    path = tmp_path / "responses.tsv"

    def submit(index: int) -> bool:
        return ResponseStore(path).submit(IDENTITY, "q1", str(index), "", "")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(submit, range(30)))

    assert sum(results) == 1
    with path.open() as file:
        assert len(file.readlines()) == 2


def test_distinct_questions_and_emails_can_submit(tmp_path: Path) -> None:
    store = ResponseStore(tmp_path / "responses.tsv")
    other = {**IDENTITY, "email": "other@example.edu", "sub": "other"}

    assert store.submit(IDENTITY, "q1", "a", "", "") is True
    assert store.submit(IDENTITY, "q2", "b", "", "") is True
    assert store.submit(other, "q1", "c", "", "") is True
    assert store.answer_counts() == {"q1": 2, "q2": 1}


def test_answer_cache_detects_external_store_writes(tmp_path: Path) -> None:
    path = tmp_path / "responses.tsv"
    reader = ResponseStore(path)
    writer = ResponseStore(path)
    writer.submit(IDENTITY, "q1", "first", "", "")
    assert reader.answers_for(IDENTITY["email"]) == {"q1": "first"}
    assert reader.answer_counts() == {"q1": 1}

    writer.submit(IDENTITY, "q2", "second", "", "")

    assert reader.answers_for(IDENTITY["email"]) == {"q1": "first", "q2": "second"}
    assert reader.answer_counts() == {"q1": 1, "q2": 1}


def test_answer_counts_update_without_recounting_loaded_cache(tmp_path: Path) -> None:
    store = ResponseStore(tmp_path / "responses.tsv")
    other = {**IDENTITY, "email": "other@example.edu", "sub": "other"}

    assert store.answer_counts() == {}
    assert store.submit(IDENTITY, "q1", "first", "", "") is True
    assert store.answer_counts() == {"q1": 1}
    assert store.submit(other, "q1", "second", "", "") is True
    assert store.answer_counts() == {"q1": 2}


def test_submit_refreshes_stale_count_cache_before_incrementing(tmp_path: Path) -> None:
    path = tmp_path / "responses.tsv"
    reader = ResponseStore(path)
    writer = ResponseStore(path)
    other = {**IDENTITY, "email": "other@example.edu", "sub": "other"}
    third = {**IDENTITY, "email": "third@example.edu", "sub": "third"}

    writer.submit(IDENTITY, "q1", "first", "", "")
    assert reader.answer_counts() == {"q1": 1}
    writer.submit(other, "q1", "second", "", "")

    assert reader.submit(third, "q1", "third", "", "") is True
    assert reader.answer_counts() == {"q1": 3}
