# Prompts

## File uploads, 28 Jun 2026

<!--
cd ~/code/liveform/
dev.sh -- codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->
<!-- SPEC: https://chatgpt.com/c/6a40f277-94d0-83ec-a517-a80bd0e895ea -->

Extend Liveform with a new `field: file`.

YAML:

- `field: file`
- optional `accept`: string or list of strings, using HTML file accept syntax like `audio/*`, `image/*`, `text/html`, `.html`, `.csv`
- optional `max_size`: human-readable size string like `500KB`, `1MB`, `5MB`; default `1MB`

Browser:

- render `<input type="file" name="answer" required>`
- set `accept` when configured
- show allowed types and max size
- validate max size before upload
- submit file questions as `multipart/form-data`; keep existing JSON flow for other fields
- show submitted upload as the saved relative path

Server:

- add `file` to supported fields
- validate `accept` and `max_size` in config
- accept multipart submissions on `POST /{slug}/answers`
- authenticate exactly like existing answers
- enforce one upload per normalized email + question using existing `ResponseStore` semantics
- save files under `<form>/uploads/<question-id>--<email-slug>--<sha256-12>.<ext>`
- infer extension from content type / allowed mapping, falling back to safe original extension
- write the relative path, e.g. `uploads/q--email--hash.ext`, as the TSV answer
- add `uploads/` to `.gitignore`
- do not publicly serve uploaded files

Write failing tests first for config parsing, rendering, upload success, type rejection, size rejection, duplicate rejection, and path sanitization. Then implement. Run and test.

---

Is this is smallest, most elegant implementation that works?
Sometimes, new features are an opportunity to refactor and simplify existing code.
What are the best opportunities to refactor and simplify existing code while adding this new feature?
List the refactoring opportunities, prioritized by impact and risk, and share them in a way that's easy for me to review.
Then await my inputs.

---

<!--
  1. Cap max_size explicitly in config
     Impact: High. Risk: Low.
     Right now src/liveform/config.py:320 accepts any MB value, while src/liveform/server.py:28 has a hard 10 MiB request cap. A form could advertise max_size: 50MB, but uploads would fail at the request
     layer. Add a clear MAX_FILE_BYTES = 5 * 1024 * 1024 or similar and reject larger config values.

  2. Remove duplicated client submit success logic
     Impact: Medium. Risk: Low.
     src/liveform/assets.py:480 has a file branch that repeats the same “delete draft, update state, render” code as the JSON path. Add a tiny applySubmitResult(question, result) helper. This is the easiest
     elegance win.

  3. Move upload helpers into a small module
     Impact: Medium. Risk: Medium-low.
     src/liveform/server.py:374 now owns MIME mapping, accept matching, extension sanitation, email slugging, and file saving. A uploads.py module would make this easier to test directly and keep server.py
     focused on routing/auth/response flow.

  4. Avoid writing files before duplicate check
     Impact: Medium. Risk: Medium.
     The current flow saves the upload, then calls ResponseStore.submit(), then deletes the just-written file on duplicate. It works, but a crash between save and submit can leave an orphan. A cleaner model
     would add a ResponseStore.has_answer(email, question) or reservation-style method before writing. This touches storage semantics, so I would only do it if orphan cleanup matters.

  5. Use a normalized submission object
     Impact: Low-medium. Risk: Low.
     src/liveform/server.py:308 returns AnswerRequest plus optional UploadFile. A small dataclass like ParsedSubmission(question_id, answer, upload) would reduce the awkward answer=None placeholder for
     multipart.
-->

Implement 1, 2 and 3.

<!-- codex resume 019f0dc2-4739-7b63-822b-25971c2be777 -->

## Efficiency, 16 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->

Make sure the front-end does not ping the back-end when it is not in focus, e.g. if another tab is in focus or the browser is minimized. This will reduce the number of requests to the server and improve efficiency. But when it comes back into focus (and it hasn't checked in the last few seconds) it should immediately check for new questions and update the display.

<!-- codex resume 019ecfd8-e794-7f53-874f-4034b0e87e58 --yolo -->

## Improve UI, 16 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->

- The numbers against the questions don't look nice. They're appearing on a line, standalone. Instead, render them in a circle at the top left of the card. Make sure it looks really good.
- The .question-title need not be bold.
- The page title should reflect the form title. For example: "Liveform: $survey_title"

---

The "# people answered" should appear as a small number below the question number circle. Just the number - with the tooltip showing what it is. That will reduce the vertical space taken up by this block.

---

The user is logged out too quickly (maybe half an hour or a few hours). Make sure they stay logged in for at least a day, if possible.

<!-- codex resume 019ecf86-d376-7741-82c1-c1f91c6139fe --yolo -->

## Live data, 16 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->

Modify the forms so that users will be able to see how many people have submitted answers to each question so far.

Do this efficiently - e.g. you may want to maintain this on the server when someone submits an answer and update it when the client polls for new questions, instead of counting the TSV file every time.

Write tests first, then implement. Run and test.

## Revisions, 13 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->

- The home page / should show an elegant link to latest form - mentioning title and description. I will share the link `https://forms.s-anand.net/` with everyone and they can just visit the page and fill in the latest form
- Instead of the .eyebrow "Liveform" show the URL of the exam, e.g. `http://localhost:3676/$DIR/` or `https://forms.s-anand.net/$DIR/`
- Instead of "Loading form..." when not logged in, show title and description.

---

- Add sequential question numbers in the form HTML - so I can tell them "Fill out question 3 now". It's OK if questions re-number when I change the YAML.
- If `field` is unspecified, default to `text` unless `choices` is present, in which case default to `single_choice`.

---

The question should appear alongside the question number. Currently, it appears on the nex line.

---

The question number should be bigger - about the same size as the question.

---

https://forms.s-anand.net/ still shows {"detail":"Form not found"} while http://localhost:3676/ shows the latest form

<!-- codex resume 019ec025-b930-7132-9661-482be4a45464 --yolo -->

## Initial draft, 12 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=high
-->

Create a Google Forms like survey application run locally and served via a Cloudflare tunnel that captures student responses to questions that I can continuously add on the go, while they're filling it out - for example, in the middle of a class or workshop.

It should require them to authenticate using a Google account. Pick up the credentials from environment variables or a local file.

I should be able to run via uvx from github without installing it.

It should be mobile friendly and include a QR code for easy access.

It should be secure: ensure one submission from verfied email ID per question with timestamp captured.

It should automatically refresh when I add a question but should be lightweight on resource usage when 200 students connect to my laptop via a Cloudflare tunnel - and also be network and resource light on a mobile browser. Maybe client polls /$DIR/version every 5–10 seconds with ETag and only fetches questions when version changes.

Adding a new question makes it appear for everyone.
Editing question text updates display but preserves old answers under the same id.
Removing or hiding a question stops showing it but does not delete responses.
Changing type for an existing id is invalid and should be warned/skipped, because old answers may no longer fit.

Users cannot edit answers once submitted. Reloading should resume from where they left off.
Use localstorage-cached Google credentials, else login if required, and show all questions, mark answered ones as submitted/read-only, and scroll to first unanswered.

I want to be able to run multiple forms/surveys, each at a different endpoint. Each has a simple YAML configuration for question-wise id, question, type, optional choices, optional description, all Markdown enabled. I will use comments for progressive reveal. Warn and skip invalid configuration.

Each answer is saved independently as a record in a TSV file with fields:

- timestamp: ISO format
- email: from Google
- name: from Google
- question: question ID from config
- answer: answer string (JSON encoded list for multi_choice, maybe others)
- ip: client's IP address
- user_agent: client's user agent string
- token_sub: subject ID from Google ID token
- email_verified: verification status of the email
- google_sub: subject ID from Google account

Users may answer available questions in any order.

I'll deploy this via https://forms.s-anand.net/$DIR/ where $DIR is the directory of the form configuration. forms.s-anand.net points to port 3676 (for "FORM"). All assets must be served from https://forms.s-anand.net/$DIR/ and not from https://forms.s-anand.net/ or /static/ or /assets/ etc.

No admin page required.

Sample file structure:

./
tds-workshop/
form.yaml
responses.tsv
ai-exam/
form.yaml
responses.tsv

... exposed as https://forms.s-anand.net/tds-workshop/ and https://forms.s-anand.net/ai-exam/

Sample schema for form.yaml:

```yaml
title: "AI Workshop Survey"
description: |
  **Markdown** content.

# Optional
auth:
  allowed_domains:
    - study.iitm.ac.in
    - ds.study.iitm.ac.in
  allowed_emails:
    - ...

questions:
  - id: q1
    field: text
    question: "Submit your link"
    description: |
      - Use bullets if useful.
    # These are based on input types in HTML
    type: "url" # optional, input type
    minlength: 10 # optional, for validation
    maxlength: 200 # optional, for validation
    pattern: "https?://.+" # optional, regex for validation
- id: q2
    field: single_choice
    question: "How useful was this?"
    choices:
      - Not useful
      - Somewhat useful
      - Very useful
  - id: q3
    field: multi_choice
    question: "What tools did you use?"
    choices:
      - ChatGPT
      - Claude
      - Gemini
      - Codex
```

`field` can be text, textarea, single_choice, multi_choice (save as JSON encoded list), maybe others.

A FastAPI app I can run something like this would be good:

```
uvx --from git+https://github.com/sanand0/liveform liveform serve ./forms \
  --port 3676 \
  --public-url https://forms.s-anand.net \
  --google-client-id "$GOOGLE_CLIENT_ID"
```

Write comprehensive tests first, THEN implement. Run and test.

---

How do I run locally? (Document in README.md.)
Do I need a redirect URL in the Google Cloud Console for OAuth? If so, what should it be for local + server? (Document in README.md.)

---

The sign-in button is too huge!
There's a little white peeking at the bottom of the page when it goes beyond a viewport height.
Use GOOGLE_CLIENT_ID=872568319651-r1jl15a1oektabjl48ch3v9dhipkpdjh.apps.googleusercontent.com and test it on localhost as well as forms.s-anand.net which points to localhost:3676 via Cloudflare tunnel.

---

The QR code shows localhost:3676/aiexam/ even when I visit https://forms.s-anand.net/aiexam/

---

Might the page reload while they are in the middle of typing an answer? How can we avoid loss of what's typed?

<!-- codex resume 019eba81-f68f-7460-94e3-86409e64591d --yolo -->
