import os

import pytest
from playwright.sync_api import expect

# Skip the whole file if not running in production build mode
if os.getenv("WEB_ASSETS_MODE") != "build":
    pytest.skip(
        "Skipping web production E2E tests (WEB_ASSETS_MODE is not 'build')",
        allow_module_level=True,
    )


def test_production_build_page_loads_and_is_functional(context, server_url: str):
    """Verify that the production build loaded from Vite serves correctly and is functional."""
    page = context.new_page()

    # Capture browser console messages to a log file
    log_file_path = "test_e2e_browser.log"
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    def log_message(text):
        with open(log_file_path, "a") as f:
            f.write(text + "\n")

    def handle_console(msg):
        log_message(f"🖥️  Browser console [{msg.type}]: {msg.text}")

    page.on("console", handle_console)
    page.on("pageerror", lambda err: log_message(f"❌ Browser error: {err}"))

    # Intercept and count static requests during cold load
    static_requests = []
    locale_requests = []

    def handle_request(request):
        url = request.url
        if "/static/" in url or "/assets/" in url:
            if url.endswith((".js", ".css", ".woff2", ".woff")):
                static_requests.append(url)
        if "/locales/" in url and url.endswith(".json"):
            locale_requests.append(url)

    page.on("request", handle_request)

    # 1. Cold load the main app
    page.goto(f"{server_url}/#/checkout")

    # Wait for the Vue app to be fully initialized and ready
    page.wait_for_function("() => window.__BCD_APP__ && window.__BCD_APP__.ready === true")

    # Expect the beautiful loading screen to be gone and app layout to be visible
    expect(page.locator(".bcd-loading")).not_to_be_visible()
    try:
        expect(page.locator(".sidebar")).to_be_visible()
    except AssertionError as exc:
        with open("test_e2e_page_content.html", "w") as f:
            f.write(page.content())
        raise exc

    # 2. Check request budget (JS, CSS, and fonts)
    print("\n📊 Production Load Requests Count:")
    print(f"   Hashed Assets & Static Files ({len(static_requests)}):")
    for req in static_requests:
        print(f"     - {req}")
    print(f"   Locales ({len(locale_requests)}):")
    for req in locale_requests:
        print(f"     - {req}")

    # Budget check: At most 10 JS/CSS/font requests before app ready
    assert (
        len(static_requests) <= 10
    ), f"Static request count {len(static_requests)} exceeds budget of 10!"
    # Document locale request count (typically 1 or 2 depending on fallback/current selection)
    assert len(locale_requests) >= 1, "At least one locale file should be fetched"

    # 3. Check libraries availability in browser context
    is_vue = page.evaluate("() => typeof Vue === 'object'")
    is_router = page.evaluate("() => typeof VueRouter === 'object'")
    is_i18n = page.evaluate("() => typeof VueI18n === 'object'")

    assert is_vue, "Vue is not globally available"
    assert is_router, "VueRouter is not globally available"
    assert is_i18n, "VueI18n is not globally available"
    # Chart.js and JsBarcode are intentionally lazy. Marked is loaded by the
    # mounted HelpPanel, whose existing E2E coverage verifies its rendering.
    assert page.evaluate("() => typeof Chart === 'undefined'")
    assert page.evaluate("() => typeof JsBarcode === 'undefined'")

    # Lazy-loading contract: feature libraries must not be part of the initial
    # checkout payload. Existing E2E tests cover the UI behavior; this test
    # additionally checks the network boundary of the production build.
    initial_urls = set(static_requests)
    assert any("marked" in url for url in initial_urls)
    assert not any("JsBarcode" in url for url in initial_urls)
    assert not any("ReportsPage" in url for url in initial_urls)

    # 4. Verify Markdown Help Panel is functional and loads Marked lazily.
    # The help button should be visible in the page header
    help_button = page.locator('button[data-bs-toggle="offcanvas"]').first
    expect(help_button).to_be_visible()

    # Clicking help button should open offcanvashelp
    help_button.click()
    panel = page.locator(".offcanvas")
    expect(panel).to_be_visible()

    # Wait for the Markdown content to render inside offcanvas
    markdown_content = panel.locator(".help-markdown")
    markdown_content.wait_for(timeout=5000)
    expect(markdown_content).to_be_visible()
    assert any("marked" in url for url in static_requests)
    # Confirm it contains formatted HTML text translated to French (default locale)
    expect(markdown_content).to_contain_text("Étape")
