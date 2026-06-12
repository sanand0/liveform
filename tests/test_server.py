import csv
import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_form_page_and_every_local_asset_are_under_form_path(client: TestClient) -> None:
    page = client.get("/workshop/")

    assert page.status_code == 200
    assert client.get("/workshop", follow_redirects=False).status_code == 200
    assert client.get("/workshop/index.html", follow_redirects=False).status_code == 200
    assert 'src="/workshop/app.js"' in page.text
    assert 'href="/workshop/app.css"' in page.text
    assert 'src="/workshop/qr.svg?v=2"' in page.text
    assert 'src="https://accounts.google.com/gsi/client"' in page.text
    assert client.get("/workshop/app.js").status_code == 200
    assert client.get("/workshop/app.css").status_code == 200
    assert client.get("/workshop/qr.svg").status_code == 200
    assert client.get("/app.js", follow_redirects=False).status_code == 404
    assert client.get("/static/app.js").status_code == 404
    assert "Math.random()" in client.get("/workshop/app.js").text
    assert 'size: "medium", width: 220' in client.get("/workshop/app.js").text
    assert "min-height: 100dvh" in client.get("/workshop/app.css").text
    assert (
        "style-src 'self' 'unsafe-inline' https://accounts.google.com"
        in page.headers["content-security-policy"]
    )


def test_qr_uses_the_origin_it_was_requested_from(client: TestClient) -> None:
    local = client.get("/workshop/qr.svg")
    public = client.get(
        "/workshop/qr.svg",
        headers={"Host": "forms.example", "X-Forwarded-Proto": "https"},
    )

    assert local.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in local.text
    assert local.headers["x-liveform-qr-target"] == "http://testserver/workshop/"
    assert public.headers["x-liveform-qr-target"] == "https://forms.example/workshop/"
    assert local.content != public.content
    assert public.headers["cache-control"] == "no-store"


def test_version_supports_etag_and_304(client: TestClient, forms_dir: Path) -> None:
    first = client.get("/workshop/version")

    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-cache"
    etag = first.headers["etag"]
    assert client.get("/workshop/version", headers={"If-None-Match": etag}).status_code == 304

    form_file = forms_dir / "workshop" / "form.yaml"
    form_file.write_text(form_file.read_text().replace("AI Workshop", "Updated Workshop"))
    changed = client.get("/workshop/version", headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != etag


def test_state_requires_auth_and_returns_public_config(client: TestClient, auth: dict) -> None:
    assert client.get("/workshop/state").status_code == 401
    response = client.get("/workshop/state", headers=auth)

    assert response.status_code == 200
    data = response.json()
    assert data["identity"]["email"] == "student@example.edu"
    assert data["answers"] == {}
    assert [question["id"] for question in data["questions"]] == [
        "link",
        "useful",
        "tools",
        "notes",
    ]
    assert "<strong>Welcome.</strong>" in data["description_html"]
    assert "<strong>link</strong>" in data["questions"][0]["question_html"]
    assert "allowed_domains" not in json.dumps(data)


def test_rejects_unverified_and_unauthorized_accounts(client: TestClient) -> None:
    unverified = client.get("/workshop/state", headers={"Authorization": "Bearer unverified-token"})
    unauthorized = client.get("/workshop/state", headers={"Authorization": "Bearer other-token"})
    explicitly_allowed = client.get(
        "/workshop/state", headers={"Authorization": "Bearer guest-token"}
    )

    assert unverified.status_code == 403
    assert unauthorized.status_code == 403
    assert explicitly_allowed.status_code == 200


def test_submit_validates_and_serializes_each_field(client: TestClient, auth: dict) -> None:
    assert (
        client.post(
            "/workshop/answers", headers=auth, json={"question": "link", "answer": "x"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/workshop/answers",
            headers=auth,
            json={"question": "link", "answer": "https://example.com"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/workshop/answers", headers=auth, json={"question": "useful", "answer": "Medium"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/workshop/answers", headers=auth, json={"question": "useful", "answer": "High"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/workshop/answers",
            headers=auth,
            json={"question": "tools", "answer": ["Codex", "ChatGPT"]},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/workshop/answers", headers=auth, json={"question": "notes", "answer": "Some notes"}
        ).status_code
        == 201
    )

    state = client.get("/workshop/state", headers=auth).json()
    assert state["answers"]["tools"] == '["Codex","ChatGPT"]'


def test_duplicate_answer_is_conflict_and_original_remains(client: TestClient, auth: dict) -> None:
    endpoint = "/workshop/answers"
    assert (
        client.post(
            endpoint, headers=auth, json={"question": "notes", "answer": "First"}
        ).status_code
        == 201
    )
    duplicate = client.post(endpoint, headers=auth, json={"question": "notes", "answer": "Second"})

    assert duplicate.status_code == 409
    assert client.get("/workshop/state", headers=auth).json()["answers"]["notes"] == "First"


def test_hidden_and_unknown_questions_cannot_be_answered(client: TestClient, auth: dict) -> None:
    for question in ("hidden", "missing"):
        response = client.post(
            "/workshop/answers", headers=auth, json={"question": question, "answer": "x"}
        )
        assert response.status_code == 404


def test_ip_prefers_cloudflare_header(client: TestClient, auth: dict, forms_dir: Path) -> None:
    response = client.post(
        "/workshop/answers",
        headers={**auth, "CF-Connecting-IP": "203.0.113.9", "User-Agent": "Test Browser"},
        json={"question": "notes", "answer": "answer"},
    )

    assert response.status_code == 201
    with (forms_dir / "workshop" / "responses.tsv").open(newline="") as file:
        row = next(csv.DictReader(file, delimiter="\t"))
    assert row["ip"] == "203.0.113.9"
    assert row["user_agent"] == "Test Browser"


def test_unknown_form_is_404(client: TestClient) -> None:
    assert client.get("/missing/").status_code == 404
    assert client.get("/missing/state").status_code == 404


def test_rejects_oversized_request_before_processing(client: TestClient, auth: dict) -> None:
    response = client.post(
        "/workshop/answers",
        headers=auth,
        content=b"x" * 1_000_001,
    )

    assert response.status_code == 413


def test_editing_question_text_preserves_existing_answer(
    client: TestClient, auth: dict, forms_dir: Path
) -> None:
    client.post("/workshop/answers", headers=auth, json={"question": "notes", "answer": "Original"})
    form_file = forms_dir / "workshop" / "form.yaml"
    form_file.write_text(
        form_file.read_text().replace("question: Notes", "question: Updated notes")
    )

    state = client.get("/workshop/state", headers=auth).json()

    notes = next(question for question in state["questions"] if question["id"] == "notes")
    assert "Updated notes" in notes["question_html"]
    assert state["answers"]["notes"] == "Original"


def test_multiple_forms_have_independent_routes_and_response_files(
    forms_dir: Path, verifier, auth: dict
) -> None:
    from liveform.server import create_app

    second = forms_dir / "second"
    second.mkdir()
    (second / "form.yaml").write_text(
        "title: Second\nquestions:\n- {id: q1, field: text, question: Second question}\n"
    )
    client = TestClient(
        create_app(forms_dir, "client-id", "https://forms.example", verifier=verifier)
    )

    assert client.get("/second/").status_code == 200
    assert (
        client.post(
            "/second/answers", headers=auth, json={"question": "q1", "answer": "second answer"}
        ).status_code
        == 201
    )
    assert (second / "responses.tsv").exists()
    assert not (forms_dir / "workshop" / "responses.tsv").exists()
