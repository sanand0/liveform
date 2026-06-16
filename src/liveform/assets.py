"""Browser assets served below each form path."""

HOME_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Latest form</title>
  <style>{css}</style>
</head>
<body>
  <main>
    <p class="eyebrow">LATEST FORM</p>
    <a class="latest-form" href="{form_url}">
      <div class="title" role="heading" aria-level="1">{title_html}</div>
      <div class="description">{description_html}</div>
      <span class="open">Open form <span aria-hidden="true">→</span></span>
    </a>
  </main>
</body>
</html>
"""

HOME_CSS = """
:root {
  color-scheme: light dark;
  --ink: #172033;
  --muted: #647087;
  --paper: #fffdf8;
  --canvas: #edf2f2;
  --line: #cad4d6;
  --accent: #b9301e;
  --shadow: #18212f22;
  font-family: "Avenir Next", Avenir, "Trebuchet MS", sans-serif;
}
* { box-sizing: border-box; }
body {
  display: grid; min-height: 100dvh; margin: 0; place-items: center; color: var(--ink);
  background:
    radial-gradient(circle at 10% 0%, color-mix(in srgb, var(--accent) 28%, transparent) 0, transparent 30rem),
    radial-gradient(circle at 100% 80%, #18745140 0, transparent 28rem),
    var(--canvas);
}
main { width: min(100% - 2rem, 700px); }
.eyebrow { margin: 0 0 .65rem; color: var(--accent); font-size: .72rem; font-weight: 800; letter-spacing: .16em; }
.latest-form {
  display: block; padding: clamp(1.5rem, 6vw, 3rem); border: 1px solid var(--line); border-radius: 1.25rem;
  background: var(--paper); color: inherit; text-decoration: none; box-shadow: 0 18px 48px var(--shadow);
  transition: transform .2s, box-shadow .2s, border-color .2s;
}
.latest-form:hover, .latest-form:focus-visible {
  transform: translateY(-3px); border-color: var(--accent); box-shadow: 0 24px 56px var(--shadow);
}
.latest-form:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
.title { font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif; font-size: clamp(2rem, 7vw, 3.8rem); font-weight: 700; line-height: 1.05; }
.title > :first-child { margin-top: 0; }
.title > :last-child { margin-bottom: .75rem; }
.description { color: var(--muted); font-size: 1.05rem; line-height: 1.6; }
.description > :last-child { margin-bottom: 0; }
.open { display: block; margin-top: 2rem; color: var(--accent); font-weight: 800; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #edf4f2; --muted: #a9b9bd; --paper: #172025; --canvas: #0d1418; --line: #35464c; --accent: #ff755e; --shadow: #0008; }
}
@media (prefers-reduced-motion: reduce) { .latest-form { transition: none; } }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Liveform: {title_text}</title>
  <link rel="icon" href="/{slug}/qr.svg?v=2" type="image/svg+xml">
  <link rel="stylesheet" href="/{slug}/app.css">
  <script src="https://accounts.google.com/gsi/client" async></script>
  <script src="/{slug}/app.js" defer></script>
</head>
<body data-slug="{slug}" data-client-id="{client_id}">
  <header>
    <div>
      <p class="eyebrow"><a href="{exam_url}">{exam_url}</a></p>
      <div id="title" class="title" role="heading" aria-level="1">{title_html}</div>
      <div id="description">{description_html}</div>
    </div>
    <aside>
      <button id="theme-toggle" class="theme-toggle" type="button">Dark mode</button>
      <figure>
        <img src="/{slug}/qr.svg?v=2" alt="QR code for this form" width="128" height="128">
        <figcaption>Scan to open</figcaption>
      </figure>
    </aside>
  </header>
  <main>
    <section id="status" class="status">Loading...</section>
    <section id="login" hidden>
      <h2>Sign in to respond</h2>
      <p>Your verified Google email identifies your submissions.</p>
      <div id="google-button"></div>
    </section>
    <div id="questions"></div>
  </main>
</body>
</html>
"""

CSS = """
:root {
  color-scheme: light;
  --ink: #172033;
  --muted: #647087;
  --paper: #fffdf8;
  --canvas: #edf2f2;
  --line: #cad4d6;
  --accent: #e14b32;
  --accent-deep: #b9301e;
  --success: #187451;
  --success-bg: #e5f7ed;
  --shadow: #18212f16;
  font-family: "Avenir Next", Avenir, "Trebuchet MS", sans-serif;
  font-size: 16px;
  line-height: 1.55;
}
:root:has(body[data-theme="dark"]) {
  color-scheme: dark;
  --ink: #edf4f2;
  --muted: #a9b9bd;
  --paper: #172025;
  --canvas: #0d1418;
  --line: #35464c;
  --accent: #ff755e;
  --accent-deep: #ff927f;
  --success: #74d7ad;
  --success-bg: #193b31;
  --shadow: #0008;
}
* { box-sizing: border-box; }
html { min-height: 100%; background: var(--canvas); }
body {
  min-height: 100dvh; margin: 0; color: var(--ink);
  background:
    radial-gradient(circle at 10% 0%, color-mix(in srgb, var(--accent) 28%, transparent) 0, transparent 30rem),
    radial-gradient(circle at 100% 30%, color-mix(in srgb, var(--success) 25%, transparent) 0, transparent 28rem),
    var(--canvas);
}
header, main { width: min(100% - 2rem, 760px); margin-inline: auto; }
header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 1.5rem;
  padding-block: 2.5rem 1.25rem;
}
aside { display: grid; justify-items: end; gap: .55rem; }
.title, .question-title { font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif; }
.title { font-weight: 700; }
.title { margin-bottom: .5rem; font-size: clamp(1.9rem, 5vw, 3rem); line-height: 1.08; }
.title > :first-child, .question-title > :first-child { margin-top: 0; }
.title > :last-child, .question-title > :last-child { margin-bottom: 0; }
h2, p { margin-top: 0; }
.eyebrow { margin-bottom: .45rem; color: var(--accent-deep); font-size: .72rem; font-weight: 800; letter-spacing: .16em; }
.eyebrow a { color: inherit; overflow-wrap: anywhere; text-decoration-thickness: .08em; text-underline-offset: .2em; }
figure { flex: 0 0 auto; margin: 0; padding: .5rem; border-radius: .85rem; background: #fff; text-align: center; box-shadow: 0 8px 24px var(--shadow); }
figure img { display: block; }
figcaption { padding-top: .25rem; color: #52606b; font-size: .72rem; }
.status { margin-bottom: 1rem; color: var(--muted); font-size: .9rem; }
.status.error { color: #b42318; }
#login, .question {
  margin-bottom: 1rem; padding: clamp(1rem, 4vw, 1.5rem); border: 1px solid var(--line);
  border-radius: 1rem; background: var(--paper); box-shadow: 0 8px 24px var(--shadow);
  animation: arrive .35s both;
}
#google-button { width: fit-content; min-height: 32px; overflow: hidden; border-radius: .35rem; }
.question:nth-child(2) { animation-delay: 40ms; }
.question:nth-child(3) { animation-delay: 80ms; }
.question:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent); }
.question { position: relative; padding-inline-start: clamp(4rem, 9vw, 4.8rem); }
.question.answered { border-left: .35rem solid var(--success); }
.question-title { margin-bottom: .35rem; font-size: 1.22rem; }
.question-rail {
  position: absolute; inset-block-start: clamp(1rem, 4vw, 1.45rem); inset-inline-start: clamp(1rem, 4vw, 1.35rem);
  display: grid; width: 2.25rem; justify-items: center; gap: .25rem;
}
.question-number {
  display: grid; width: 2.25rem; aspect-ratio: 1; place-items: center; border: 1px solid color-mix(in srgb, var(--accent) 70%, #fff);
  border-radius: 50%; background: linear-gradient(145deg, var(--accent), var(--accent-deep)); color: #fff;
  font-family: "Avenir Next", Avenir, "Trebuchet MS", sans-serif; font-size: .92rem; font-weight: 800; line-height: 1;
  box-shadow: 0 .45rem 1rem color-mix(in srgb, var(--accent) 28%, transparent);
}
.question-count {
  color: var(--muted); font-family: "Avenir Next", Avenir, "Trebuchet MS", sans-serif;
  font-size: .76rem; font-weight: 800; line-height: 1; text-align: center;
}
.description { color: var(--muted); font-size: .92rem; }
.description > :last-child, #description > :last-child { margin-bottom: 0; }
label.choice { display: flex; gap: .65rem; align-items: flex-start; padding: .55rem 0; }
input[type="radio"], input[type="checkbox"] { width: 1.15rem; height: 1.15rem; margin-top: .2rem; accent-color: var(--accent); }
input[type="text"], input[type="url"], input[type="email"], input[type="tel"], input[type="number"],
input[type="date"], input[type="time"], input[type="datetime-local"], textarea {
  width: 100%; margin-top: .8rem; padding: .75rem; border: 1px solid var(--line); border-radius: .55rem;
  background: var(--paper); color: inherit; font: inherit;
}
textarea { min-height: 7rem; resize: vertical; }
button {
  margin-top: 1rem; padding: .65rem 1rem; border: 0; border-radius: .55rem; background: var(--accent);
  color: #fff; font: inherit; font-weight: 700; cursor: pointer;
}
button:hover { background: var(--accent-deep); }
button:focus-visible, input:focus-visible, textarea:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
button:disabled { cursor: wait; opacity: .6; }
.theme-toggle { margin: 0; padding: .45rem .7rem; border: 1px solid var(--line); background: var(--paper); color: var(--ink); font-size: .78rem; }
.theme-toggle:hover { background: var(--canvas); }
.submitted { margin: .85rem 0 0; padding: .75rem; border-radius: .55rem; background: var(--success-bg); white-space: pre-wrap; overflow-wrap: anywhere; }
.submitted strong { display: block; color: var(--success); font-size: .78rem; letter-spacing: .05em; text-transform: uppercase; }
.field-error { margin-top: .75rem; color: #b42318; }
@keyframes arrive { from { opacity: 0; transform: translateY(.5rem); } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .001ms !important; scroll-behavior: auto !important; } }
@media (max-width: 560px) {
  header { padding-top: 1.25rem; }
  figure { display: none; }
  header, main { width: min(100% - 1rem, 760px); }
}
"""

JS = r"""
// @ts-check
const { slug, clientId } = document.body.dataset;
const base = `/${slug}`;
const tokenKey = `liveform.google-token:${clientId}`;
const themeKey = "liveform.theme";
const status = document.querySelector("#status");
const login = document.querySelector("#login");
const questions = document.querySelector("#questions");
const themeToggle = document.querySelector("#theme-toggle");
let token = localStorage.getItem(tokenKey);
let state;
let etag;
const drafts = new Map();

const draftKey = () => `liveform.drafts:${clientId}:${slug}:${state?.identity?.email ?? ""}`;
const saveDrafts = () => sessionStorage.setItem(draftKey(), JSON.stringify(Object.fromEntries(drafts)));
const loadDrafts = () => {
  drafts.clear();
  try {
    for (const [question, answer] of Object.entries(JSON.parse(sessionStorage.getItem(draftKey()) ?? "{}"))) drafts.set(question, answer);
  } catch {
    sessionStorage.removeItem(draftKey());
  }
};

const setTheme = (theme) => {
  document.body.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "Light mode" : "Dark mode";
};
setTheme(localStorage.getItem(themeKey) ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
themeToggle.addEventListener("click", () => {
  const theme = document.body.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem(themeKey, theme);
  setTheme(theme);
});

const setStatus = (message, error = false) => {
  status.textContent = message;
  status.classList.toggle("error", error);
};

const api = async (path, options = {}) => {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", ...options.headers },
  });
  const data = response.status === 204 ? null : await response.json();
  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem(tokenKey);
    token = null;
    showLogin();
    throw new Error(response.status === 403 ? "This account is not allowed. Sign in with another account." : "Your sign-in expired. Sign in again.");
  }
  if (!response.ok) {
    const error = new Error(data?.detail ?? "Request failed");
    error.status = response.status;
    throw error;
  }
  return data;
};

const showLogin = () => {
  login.hidden = false;
  questions.replaceChildren();
  setStatus("Sign in with a verified Google account.");
  const render = () => {
    google.accounts.id.initialize({
      client_id: clientId,
      callback: ({ credential }) => {
        token = credential;
        localStorage.setItem(tokenKey, token);
        login.hidden = true;
        loadState(true).catch(showError);
      },
    });
    google.accounts.id.renderButton(document.querySelector("#google-button"), {
      theme: "outline", size: "medium", width: 220,
    });
  };
  window.google?.accounts?.id ? render() : setTimeout(showLogin, 300);
};

const showError = (error) => setStatus(error.message ?? String(error), true);

const addConstraint = (element, question, name) => {
  if (question[name] !== undefined) element.setAttribute(name, question[name]);
};

const buildField = (question) => {
  if (question.field === "text" || question.field === "textarea") {
    const element = document.createElement(question.field === "textarea" ? "textarea" : "input");
    element.name = "answer";
    element.required = true;
    if (question.field === "text") element.type = question.type ?? "text";
    for (const name of ["minlength", "maxlength", "pattern"]) addConstraint(element, question, name);
    return element;
  }
  const fragment = document.createDocumentFragment();
  for (const choice of question.choices) {
    const label = document.createElement("label");
    label.className = "choice";
    const input = document.createElement("input");
    input.type = question.field === "single_choice" ? "radio" : "checkbox";
    input.name = "answer";
    input.value = choice;
    input.required = question.field === "single_choice";
    label.append(input, document.createTextNode(choice));
    fragment.append(label);
  }
  return fragment;
};

const displayAnswer = (answer) => {
  try {
    const value = JSON.parse(answer);
    return Array.isArray(value) ? value.join(", ") : answer;
  } catch {
    return answer;
  }
};

const countText = (count) => `${count} ${count === 1 ? "person" : "people"} answered`;
const setCount = (element, count) => {
  const label = countText(count);
  element.textContent = `${count}`;
  element.title = label;
  element.ariaLabel = label;
};

const updateCounts = () => {
  for (const question of state.questions) {
    const count = state.answer_counts?.[question.id] ?? 0;
    const element = document.querySelector(`#question-${question.id} .question-count`);
    if (element) setCount(element, count);
  }
};

const rememberDraft = (question, form) => {
  const data = new FormData(form);
  drafts.set(question.id, question.field === "multi_choice" ? data.getAll("answer") : data.get("answer"));
  saveDrafts();
};

const restoreDraft = (question, form) => {
  if (!drafts.has(question.id)) return;
  const draft = drafts.get(question.id);
  for (const input of form.querySelectorAll("[name=answer]")) {
    if (input.type === "radio" || input.type === "checkbox") input.checked = (Array.isArray(draft) ? draft : [draft]).includes(input.value);
    else input.value = draft;
  }
};

const render = (scroll = false) => {
  document.title = `Liveform: ${state.title_text}`;
  document.querySelector("#title").innerHTML = state.title_html;
  document.querySelector("#description").innerHTML = state.description_html;
  questions.replaceChildren();
  for (const [index, question] of state.questions.entries()) {
    const article = document.createElement("article");
    article.className = "question";
    article.id = `question-${question.id}`;
    const title = document.createElement("div");
    title.className = "question-title";
    title.role = "heading";
    title.ariaLevel = "2";
    const rail = document.createElement("div");
    rail.className = "question-rail";
    const number = document.createElement("span");
    number.className = "question-number";
    number.textContent = `${index + 1}`;
    const count = document.createElement("span");
    count.className = "question-count";
    setCount(count, state.answer_counts?.[question.id] ?? 0);
    rail.append(number, count);
    article.append(rail);
    title.insertAdjacentHTML("beforeend", question.question_html);
    article.append(title);
    if (question.description_html) {
      const description = document.createElement("div");
      description.className = "description";
      description.innerHTML = question.description_html;
      article.append(description);
    }
    if (state.answers[question.id] !== undefined) {
      article.classList.add("answered");
      const submitted = document.createElement("p");
      submitted.className = "submitted";
      const label = document.createElement("strong");
      label.textContent = "Submitted";
      submitted.append(label, document.createTextNode(displayAnswer(state.answers[question.id])));
      article.append(submitted);
    } else {
      const form = document.createElement("form");
      form.append(buildField(question));
      const button = document.createElement("button");
      button.type = "submit";
      button.textContent = "Submit answer";
      const error = document.createElement("p");
      error.className = "field-error";
      form.append(button, error);
      restoreDraft(question, form);
      form.addEventListener("input", () => rememberDraft(question, form));
      form.addEventListener("change", () => rememberDraft(question, form));
      form.addEventListener("submit", event => submit(event, question, button, error));
      article.append(form);
    }
    questions.append(article);
  }
  setStatus(`${state.identity.name || state.identity.email} · ${Object.keys(state.answers).length} submitted`);
  if (scroll) questions.querySelector(".question:not(.answered)")?.scrollIntoView({ behavior: "smooth", block: "center" });
};

const submit = async (event, question, button, error) => {
  event.preventDefault();
  button.disabled = true;
  error.textContent = "";
  try {
    const data = new FormData(event.currentTarget);
    const answer = question.field === "multi_choice" ? data.getAll("answer") : data.get("answer");
    if (question.field === "multi_choice" && !answer.length) throw new Error("Select at least one choice.");
    const result = await api("/answers", { method: "POST", body: JSON.stringify({ question: question.id, answer }) });
    drafts.delete(question.id);
    saveDrafts();
    state.answers[question.id] = result.answer;
    state.answer_counts = result.answer_counts;
    render(false);
  } catch (cause) {
    if (cause.status === 409) {
      await loadState(false);
      return;
    }
    error.textContent = cause.message ?? String(cause);
    button.disabled = false;
  }
};

const loadState = async (scroll = false) => {
  state = await api("/state");
  loadDrafts();
  etag = `"${state.version}"`;
  login.hidden = true;
  render(scroll);
};

const poll = async () => {
  if (!token || document.hidden) return;
  try {
    const nextState = await api("/state");
    const needsRender = !state || nextState.version !== state.version || JSON.stringify(nextState.answers) !== JSON.stringify(state.answers);
    const scroll = Boolean(state && nextState.version !== state.version);
    state = nextState;
    etag = `"${state.version}"`;
    if (needsRender) {
      loadDrafts();
      render(scroll);
      return;
    }
    updateCounts();
    setStatus(`${state.identity.name || state.identity.email} · ${Object.keys(state.answers).length} submitted`);
  } catch (error) {
    if (!token) return;
    setStatus("Offline. Retrying automatically.", true);
  }
};

document.addEventListener("visibilitychange", () => !document.hidden && poll());
const schedulePoll = () => setTimeout(async () => {
  await poll();
  schedulePoll();
}, 5000 + Math.random() * 5000);
schedulePoll();
token ? loadState(true).catch(showError) : showLogin();
"""
