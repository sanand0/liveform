"""Real-browser interaction and screenshot smoke test."""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT = Path("/tmp/liveform-browser")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 390, "height": 844})
    context.add_init_script(
        "localStorage.setItem('liveform.google-token:browser-client', 'student-token')"
    )
    page = context.new_page()
    page.goto("http://127.0.0.1:8765/tds-workshop/")
    page.wait_for_load_state("networkidle")

    assert page.get_by_text("AI Workshop Survey").is_visible()
    assert page.locator(".question").count() == 3
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
