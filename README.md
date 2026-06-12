# liveform

Liveform runs continuously editable classroom surveys on your laptop. Students sign in with
Google, answer each question once, and see new questions automatically without reloading.
Responses are append-only TSV records stored beside each form.

## Google Cloud Setup

Create an OAuth client in Google Cloud Console:

1. Configure the OAuth consent screen. While the app is in testing mode, add the Google accounts
   that will test it under **Test users**.
2. Go to **APIs & Services > Credentials > Create credentials > OAuth client ID**.
3. Select **Web application**.
4. Add these **Authorized JavaScript origins** as needed:

   ```text
   http://localhost:3676
   http://127.0.0.1:3676
   https://forms.s-anand.net
   ```

   Add `localhost` when opening the local form as `http://localhost:3676/...`. Add `127.0.0.1`
   when opening it as `http://127.0.0.1:3676/...`. Origins contain only the scheme, hostname, and
   optional port: do not include a trailing slash or form path.

5. Copy the generated client ID, which ends in `.apps.googleusercontent.com`.

**Authorized redirect URIs are not required.** Liveform uses Google Identity Services' popup mode
with a JavaScript callback, then sends the returned ID token to Liveform for server-side
verification. It does not use Google's redirect UX mode or expose an OAuth callback endpoint.

## Run Locally

From a repository checkout, use the included sample form:

```bash
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"

uv run liveform serve ./forms \
  --port 3676 \
  --google-client-id "$GOOGLE_CLIENT_ID"
```

Open <http://localhost:3676/tds-workshop/>. The page also shows a QR code, but phones cannot reach
your computer through `localhost`; use the Cloudflare tunnel setup below when students need to
connect from other devices. QR codes use the origin through which the form is opened: opening the
same form through `https://forms.s-anand.net/...` produces a public tunnel URL in its QR code.

The sample form allows only `study.iitm.ac.in` domains. To test with another verified Google
account, edit its `auth.allowed_domains` / `auth.allowed_emails`, or remove the `auth` section to
allow any verified Google account.

To run the published GitHub version without cloning or installing it, create your own `./forms`
directory and run:

```bash
uvx --from git+https://github.com/sanand0/liveform liveform serve ./forms \
  --port 3676 \
  --google-client-id "$GOOGLE_CLIENT_ID"
```

You can omit `--google-client-id` when `GOOGLE_CLIENT_ID` is set. Liveform also accepts
`--credentials-file client_secret.json` for a downloaded Google OAuth web-client JSON file.

## Run from GitHub

Create one directory per form:

```text
forms/
  tds-workshop/
    form.yaml
  ai-exam/
    form.yaml
```

Then run:

```bash
uvx --from git+https://github.com/sanand0/liveform liveform serve ./forms \
  --port 3676 \
  --google-client-id "$GOOGLE_CLIENT_ID"
```

For an existing Cloudflare tunnel, route `forms.s-anand.net` to
`http://localhost:3676`. Liveform binds to `127.0.0.1` by default. Each form and all of its local
assets are served below its own path, such as `https://forms.s-anand.net/tds-workshop/`.
The only external browser asset is Google Identity Services, loaded from `accounts.google.com` for
sign-in.

The Google OAuth web client must list `https://forms.s-anand.net` under **Authorized JavaScript
origins**. No production redirect URI is required.

## Google Client ID

Liveform accepts the Google OAuth web client ID from the first available source:

1. `--google-client-id`
2. `GOOGLE_CLIENT_ID`
3. `--credentials-file` containing the client ID or a downloaded Google OAuth JSON file
4. `GOOGLE_APPLICATION_CREDENTIALS` pointing to either file format

The client ID is public and is sent to the browser. A client secret is not needed. Google ID
tokens are verified server-side for the configured client ID. The browser caches its ID token in
local storage, protected by a strict Content Security Policy; this avoids repeated sign-ins but
means students should not use an untrusted shared browser profile.

## Form Configuration

See [`forms/tds-workshop/form.yaml`](examples/forms/tds-workshop/form.yaml).

```yaml
title: "AI Workshop Survey"
description: |
  **Markdown** content.

auth:
  allowed_domains:
    - study.iitm.ac.in
  allowed_emails:
    - guest@gmail.com

questions:
  - id: link
    field: text
    question: "Submit your **link**"
    description: "Use a public URL."
    type: url
    minlength: 10
    maxlength: 200
    pattern: "https?://.+"

  - id: useful
    field: single_choice
    question: "How useful was this?"
    choices: [Not useful, Somewhat useful, Very useful]

  - id: tools
    field: multi_choice
    question: "What tools did you use?"
    choices: [ChatGPT, Gemini, Codex]
```

Supported `field` values are `text`, `textarea`, `single_choice`, and `multi_choice`. Text fields
also support safe HTML input types plus `minlength`, `maxlength`, and `pattern`. Validation runs in
both the browser and server. Markdown is rendered and sanitized server-side.

Authorization allows any verified Google email when `auth` is omitted. When rules exist, an email
is allowed if it matches either `allowed_emails` or `allowed_domains`.

- Add a question to reveal it on the next 7.5-second client poll.
- Edit question text, descriptions, choices, or validation while retaining existing answers.
- Set `hidden: true` or remove a question to stop showing it without deleting responses.
- Do not reuse an ID for a different `field`. Liveform persists original fields in
  `.liveform-types.json` and warns and skips changed IDs, including after restart.
- Syntax errors retain the last valid in-memory configuration while you finish editing.
- Invalid individual questions are logged and skipped.
- Invalid authorization configuration fails closed and returns 503 until corrected.

Automatic question updates do not reload the page. Unsubmitted input is preserved while questions
re-render and in per-tab `sessionStorage`, so it also survives an accidental browser reload.
Drafts are scoped to the form and signed-in email and removed after successful submission.

## Responses

Each accepted answer is appended independently to `<form>/responses.tsv`:

```text
timestamp	email	name	question	answer	ip	user_agent	token_sub	email_verified	google_sub
```

`multi_choice` answers are compact JSON lists. A file lock makes the check-and-append operation
atomic across concurrent requests and server processes. The unique key is the normalized verified
Google email plus question ID. Submitted answers cannot be edited through the application.
Requests above 1 MB and individual text answers above 100,000 characters are rejected.

`responses.tsv`, local credential files, and `.liveform-types.json` are ignored by Git by default
because they contain PII, credentials, or local state. Back them up separately.
Treat response text as untrusted when importing it into spreadsheet software.

## Development

```bash
uv run pytest -q
uvx ruff check .
uvx ruff format --check .
```

The small unauthenticated `/<form>/version` endpoint supports ETag/304 responses. Clients poll on a
jittered 5-10 second interval and fetch authenticated form state only after the validated public
configuration version changes. Parsed response indexes and QR SVGs are cached in memory and
invalidated when their backing data changes.
