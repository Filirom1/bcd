"""
Simple test to check if borrowers page loads
"""
from playwright.sync_api import Page


def test_borrowers_page_loads(page: Page, server_url: str, db_session):
    """Test that borrowers page loads successfully."""
    # Capture console errors
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"{msg.type}: {msg.text}"))

    # Capture page errors
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    # Navigate to borrowers page
    page.goto(f"{server_url}/#/borrowers")
    page.wait_for_timeout(5000)

    # Take screenshot for debugging
    page.screenshot(path="/tmp/borrowers_page.png")

    # Check if page title exists
    title = page.locator('h1, h2, h3').first
    print("Looking for page title...")

    # Check if any Vue app element exists
    app_element = page.locator('#app, .borrowers-page, .container').first
    print("Looking for app element...")

    # Print page HTML for debugging
    html = page.content()
    print(f"Page HTML length: {len(html)}")
    print(f"HTML content:\n{html}")

    # Check if admin button exists
    admin_button = page.locator('button.btn-danger.dropdown-toggle')
    print(f"Admin button count: {admin_button.count()}")

    # Try to wait for any button
    any_button = page.locator('button').first
    print(f"Any button count: {page.locator('button').count()}")

    # Print console messages and errors
    print(f"\n=== Console Messages ({len(console_messages)}) ===")
    for msg in console_messages[-20:]:  # Last 20 messages
        print(f"  {msg}")

    print(f"\n=== Page Errors ({len(page_errors)}) ===")
    for error in page_errors:
        print(f"  {error}")
