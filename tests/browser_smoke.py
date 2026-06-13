"""Real-browser interaction and screenshot smoke test."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT = Path("/tmp/liveform-browser")
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    anonymous = browser.new_page(viewport={"width": 390, "height": 844})
    anonymous.goto("http://127.0.0.1:8765/")
    anonymous.wait_for_load_state("networkidle")
    latest = anonymous.locator(".latest-form")
    assert latest.is_visible()
    assert (latest.get_attribute("href") or "").startswith("http://127.0.0.1:8765/")
    anonymous.screenshot(path=OUTPUT / "home-mobile.png", full_page=True)

    anonymous.goto("http://127.0.0.1:8765/tds-workshop/")
    anonymous.wait_for_load_state("networkidle")
    assert anonymous.get_by_text("AI Workshop Survey").is_visible()
    assert anonymous.locator("#description").inner_text()
    assert anonymous.locator(".eyebrow").inner_text() == "http://127.0.0.1:8765/tds-workshop/"
    assert "Loading form..." not in anonymous.locator("body").inner_text()
    assert anonymous.locator("#login").is_visible()
    anonymous.screenshot(path=OUTPUT / "logged-out-mobile.png", full_page=True)
    anonymous.close()

    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(
        "localStorage.setItem('liveform.google-token:browser-client', 'student-token')"
    )
    page = context.new_page()
    page.goto("http://127.0.0.1:8765/tds-workshop/")
    page.wait_for_load_state("networkidle")

    assert page.get_by_text("AI Workshop Survey").is_visible()
    assert page.locator(".question").count() == 3
    assert page.locator(".question-number").all_inner_texts() == ["1.", "2.", "3."]
    page.locator("#question-useful input[value='Very useful']").check()
    page.locator("#question-link input").fill("https://example.com/project")
    page.locator("#question-link button").click()
    page.locator("#question-link .submitted").wait_for()
    assert "https://example.com/project" in page.locator("#question-link .submitted").inner_text()
    assert page.locator("#question-useful input[value='Very useful']").is_checked()

    page.locator("#theme-toggle").click()
    assert page.locator("body").get_attribute("data-theme") == "dark"
    assert page.locator(".title").evaluate(
        """node => {
          const channels = getComputedStyle(node).color.match(/\\d+/g).slice(0, 3).map(Number);
          return channels.reduce((total, value) => total + value, 0) > 600;
        }"""
    )
    page.screenshot(path=OUTPUT / "mobile-dark.png", full_page=True)

    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.locator("#question-link .submitted").is_visible()
    assert page.locator("#question-useful input[value='Very useful']").is_checked()
    browser.close()
