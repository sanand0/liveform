import json
import logging
from pathlib import Path

import pytest

from liveform.config import ConfigError, FormRegistry


def write_form(path: Path, content: str) -> None:
    path.mkdir(exist_ok=True)
    (path / "form.yaml").write_text(content)


def test_discovers_only_directories_with_form_yaml(tmp_path: Path) -> None:
    write_form(tmp_path / "one", "title: One\nquestions: []\n")
    (tmp_path / "empty").mkdir()
    (tmp_path / "file.txt").write_text("no")

    registry = FormRegistry(tmp_path)

    assert registry.slugs() == ["one"]


def test_skips_invalid_questions_and_renders_markdown(tmp_path: Path, caplog) -> None:
    write_form(
        tmp_path / "one",
        """\
title: "**Title**"
description: "<script>alert(1)</script> Hello"
questions:
  - id: good
    field: text
    question: "**Valid**"
  - id: duplicate
    field: text
    question: First
  - id: duplicate
    field: text
    question: Second
  - id: bad-choice
    field: single_choice
    question: No choices
  - id: bad-field
    field: unsupported
    question: No
  - field: text
    question: No id
""",
    )

    with caplog.at_level(logging.WARNING):
        form = FormRegistry(tmp_path).get("one")

    assert [question.id for question in form.questions] == ["good", "duplicate"]
    assert "<strong>Title</strong>" in form.title_html
    assert "<script>" not in form.description_html
    assert "<strong>Valid</strong>" in form.questions[0].question_html
    assert "Skipping" in caplog.text


def test_hidden_questions_are_valid_but_not_public(tmp_path: Path) -> None:
    write_form(
        tmp_path / "one",
        """\
title: One
questions:
  - id: visible
    field: text
    question: Visible
  - id: hidden
    field: text
    question: Hidden
    hidden: true
""",
    )
    form = FormRegistry(tmp_path).get("one")

    assert [question.id for question in form.questions] == ["visible"]
    assert form.question("hidden") is None


def test_field_defaults_to_text_or_single_choice_when_omitted(tmp_path: Path) -> None:
    write_form(
        tmp_path / "one",
        """\
title: One
questions:
  - id: text
    question: Your name
  - id: choice
    question: Pick one
    choices: [First, Second]
""",
    )

    form = FormRegistry(tmp_path).get("one")

    assert form.question("text").field == "text"
    assert form.question("choice").field == "single_choice"
    assert form.question("choice").choices == ("First", "Second")


def test_changed_field_is_skipped_and_original_types_persist(tmp_path: Path, caplog) -> None:
    path = tmp_path / "one"
    write_form(path, "title: One\nquestions:\n- {id: q1, field: text, question: First}\n")
    registry = FormRegistry(tmp_path)
    assert registry.get("one").question("q1").field == "text"

    (path / "form.yaml").write_text(
        "title: One\nquestions:\n- {id: q1, field: textarea, question: Changed}\n"
    )
    with caplog.at_level(logging.WARNING):
        assert registry.get("one").question("q1") is None

    persisted = json.loads((path / ".liveform-types.json").read_text())
    assert persisted == {"q1": "text"}
    assert "cannot change field" in caplog.text

    restarted = FormRegistry(tmp_path)
    assert restarted.get("one").question("q1") is None


def test_invalid_yaml_keeps_last_valid_config(tmp_path: Path, caplog) -> None:
    path = tmp_path / "one"
    write_form(path, "title: One\nquestions:\n- {id: q1, field: text, question: First}\n")
    registry = FormRegistry(tmp_path)
    first = registry.get("one")
    (path / "form.yaml").write_text("title: [broken")

    with caplog.at_level(logging.WARNING):
        second = registry.get("one")

    assert second.version == first.version
    assert second.question("q1") is not None
    assert "Keeping previous valid configuration" in caplog.text


def test_text_constraints_are_validated_in_config(tmp_path: Path) -> None:
    write_form(
        tmp_path / "one",
        """\
title: One
questions:
  - {id: bad, field: text, question: Bad, minlength: 5, maxlength: 2}
  - {id: regex, field: text, question: Bad regex, pattern: "["}
  - {id: good, field: textarea, question: Good, maxlength: 20}
""",
    )
    form = FormRegistry(tmp_path).get("one")

    assert [question.id for question in form.questions] == ["good"]


def test_version_changes_for_text_edit_but_not_yaml_comments(tmp_path: Path) -> None:
    path = tmp_path / "one"
    original = "title: One\nquestions:\n- {id: q1, field: text, question: First}\n"
    write_form(path, original)
    registry = FormRegistry(tmp_path)
    first = registry.get("one").version

    (path / "form.yaml").write_text("# reveal later\n" + original)
    assert registry.get("one").version == first

    (path / "form.yaml").write_text(original.replace("First", "Updated"))
    assert registry.get("one").version != first


def test_malformed_auth_fails_closed(tmp_path: Path) -> None:
    write_form(
        tmp_path / "one",
        "title: One\nauth:\n  allowed_domains: example.edu\nquestions: []\n",
    )

    with pytest.raises(ConfigError, match="allowed_domains"):
        FormRegistry(tmp_path).get("one")


def test_malformed_auth_reload_does_not_preserve_broader_access(tmp_path: Path) -> None:
    path = tmp_path / "one"
    write_form(path, "title: One\nquestions: []\n")
    registry = FormRegistry(tmp_path)
    registry.get("one")
    (path / "form.yaml").write_text(
        "title: One\nauth:\n  allowed_domains: example.edu\nquestions: []\n"
    )

    with pytest.raises(ConfigError, match="authorization"):
        registry.get("one")
