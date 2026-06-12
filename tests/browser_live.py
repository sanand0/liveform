"""Verify the real Google sign-in UI on localhost and the public tunnel."""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT = Path("/tmp/liveform-live")
OUTPUT.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for index, url in enumerate(sys.argv[1:]):
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors: list[str] = []
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" else None,
        )
        response = page.goto(url)
        assert response and response.ok, f"{url}: HTTP {response.status if response else 'unknown'}"
        button = page.locator("#google-button iframe")
        button.wait_for(state="attached", timeout=15_000)
        page.wait_for_timeout(2_000)
        box = button.bounding_box()
        details = button.evaluate(
            """node => ({
              display: getComputedStyle(node).display,
              visibility: getComputedStyle(node).visibility,
              width: node.getAttribute("width"),
              height: node.getAttribute("height"),
              src: node.getAttribute("src"),
            })"""
        )
        print(url, box, details, errors)
        assert "width=220" in details["src"], f"{url}: Google iframe width is {details}"
        assert not box or (box["width"] <= 220 and box["height"] <= 40), (
            f"{url}: Google button is {box}"
        )
        assert not any(
            "content security policy" in error.lower() and "cloudflareinsights.com" not in error
            for error in errors
        ), errors
        origin_allowed = not any("origin is not allowed" in error.lower() for error in errors)

        page.evaluate(
            """() => {
              const spacer = document.createElement("div");
              spacer.style.height = "1200px";
              document.body.append(spacer);
            }"""
        )
        page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
        colors = page.evaluate(
            """() => ({
              html: getComputedStyle(document.documentElement).backgroundColor,
              body: getComputedStyle(document.body).backgroundColor,
            })"""
        )
        assert colors["html"] != "rgba(0, 0, 0, 0)", f"{url}: transparent root background"
        assert colors["body"] != "rgba(0, 0, 0, 0)", f"{url}: transparent body background"
        page.screenshot(path=OUTPUT / f"{index}.png", full_page=True)
        print(url, colors, {"google_origin_allowed": origin_allowed})
        page.close()
    browser.close()
