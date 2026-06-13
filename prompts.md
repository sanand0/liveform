# Prompts

## Revisions, 13 Jun 2026

<!--
cd ~/code/liveform/
dev.sh
codex --yolo --model gpt-5.5 --config model_reasoning_effort=medium
-->

- The home page / should show an elegant link to latest form - mentioning title and description. I will share the link `https://forms.s-anand.net/` with everyone and they can just visit the page and fill in the latest form
- Instead of the .eyebrow "Liveform" show the URL of the exam, e.g. `http://localhost:3676/$DIR/` or `https://forms.s-anand.net/$DIR/`
- Instead of "Loading form..." when not logged in, show title and description.

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
