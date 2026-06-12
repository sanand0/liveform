import json
from pathlib import Path

from typer.testing import CliRunner

from liveform.cli import app, preflight, resolve_client_id


def test_client_id_precedence_and_google_credentials_formats(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "environment-id")
    assert resolve_client_id("argument-id", None) == "argument-id"
    assert resolve_client_id(None, None) == "environment-id"

    monkeypatch.delenv("GOOGLE_CLIENT_ID")
    simple = tmp_path / "simple.txt"
    simple.write_text("simple-id\n")
    assert resolve_client_id(None, simple) == "simple-id"

    downloaded = tmp_path / "credentials.json"
    downloaded.write_text(json.dumps({"web": {"client_id": "downloaded-id"}}))
    assert resolve_client_id(None, downloaded) == "downloaded-id"


def test_serve_requires_client_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    result = CliRunner().invoke(app, ["serve", str(tmp_path)])

    assert result.exit_code != 0
    assert "Google client ID" in result.output


def test_preflight_loads_forms_and_checks_response_write_access(tmp_path: Path) -> None:
    form = tmp_path / "one"
    form.mkdir()
    (form / "form.yaml").write_text(
        "title: One\nquestions:\n- {id: q1, field: text, question: First}\n"
    )

    assert preflight(tmp_path) == ["one"]
    assert (form / "responses.tsv").exists()
