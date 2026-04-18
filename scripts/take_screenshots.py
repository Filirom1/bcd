#!/usr/bin/env python3
"""
Take screenshots of BCD Vue application for documentation.

This script captures screenshots of all main pages in the BCD web interface.
Run this periodically to keep documentation screenshots up to date.

Usage:
    python scripts/take_screenshots.py

Requirements:
    - BCD server must be running on http://127.0.0.1:8000
    - Playwright must be installed: pip install playwright
    - Playwright browsers: playwright install chromium

Output:
    Screenshots saved to docs/screenshots/
"""

import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright


async def take_screenshots(base_url="http://127.0.0.1:8000"):
    """Take screenshots of all BCD pages.

    Args:
        base_url: Base URL of the BCD application
    """
    print(f"Taking screenshots from {base_url}")
    print("=" * 60)

    # Define pages to screenshot
    pages_to_capture = [
        {
            'name': 'Checkout',
            'path': '/#/checkout',
            'filename': '01-checkout.png',
            'wait_selector': '.circulation-page',
        },
        {
            'name': 'Return',
            'path': '/#/return',
            'filename': '02-return.png',
            'wait_selector': '.circulation-page',
        },
        {
            'name': 'Catalog',
            'path': '/#/catalog',
            'filename': '03-catalog.png',
            'wait_selector': '.catalog-page',
        },
        {
            'name': 'Cataloging (ISBN step)',
            'path': '/#/cataloging',
            'filename': '04-cataloging.png',
            'wait_selector': '.cataloging-page',
        },
        {
            'name': 'Borrowers',
            'path': '/#/borrowers',
            'filename': '05-borrowers.png',
            'wait_selector': '.borrowers-page',
        },
        {
            'name': 'Classes',
            'path': '/#/classes',
            'filename': '06-classes.png',
            'wait_selector': '.classes-page',
        },
        {
            'name': 'Reports — Overdue',
            'path': '/#/reports/overdue',
            'filename': '07-reports-overdue.png',
            'wait_selector': '.reports-page',
        },
        {
            'name': 'Reports — Most Borrowed',
            'path': '/#/reports/most-borrowed',
            'filename': '08-reports-most-borrowed.png',
            'wait_selector': '.reports-page',
        },
        {
            'name': 'Reports — Never Borrowed',
            'path': '/#/reports/never-borrowed',
            'filename': '09-reports-never-borrowed.png',
            'wait_selector': '.reports-page',
        },
        {
            'name': 'Settings',
            'path': '/#/settings',
            'filename': '10-settings.png',
            'wait_selector': '.settings-page',
        },
        {
            'name': 'Print — Student Cards',
            'path': '/#/print/borrowers/cards',
            'filename': '11-print-cards.png',
            'wait_selector': '.print-page, .print-container, body',
        },
        {
            'name': 'Print — Item Labels',
            'path': '/#/print/catalog/labels',
            'filename': '12-print-labels.png',
            'wait_selector': '.print-page, .labels-container, body',
        },
    ]

    # Ensure output directory exists
    output_dir = Path('docs/screenshots')
    output_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='fr-FR'
        )
        page = await context.new_page()

        try:
            # Test if server is running
            print(f"\nChecking if server is running at {base_url}...")
            response = await page.goto(base_url, wait_until='networkidle', timeout=5000)

            if response.status != 200:
                print(f"ERROR: Server returned status {response.status}")
                print("\nPlease start the BCD server first:")
                print("  python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
                return False

            print("Server is running")
            print()

            # Take screenshots
            for page_info in pages_to_capture:
                print(f"Capturing: {page_info['name']}...", end=' ', flush=True)

                # Navigate to page
                url = f"{base_url}{page_info['path']}"
                await page.goto(url, wait_until='networkidle')

                # Wait for page-specific selector
                try:
                    await page.wait_for_selector(
                        page_info['wait_selector'],
                        timeout=5000
                    )
                except Exception:
                    # Fallback: just wait a bit
                    await page.wait_for_timeout(1500)

                # Additional wait for dynamic content (API calls, rendering)
                await page.wait_for_timeout(800)

                # Take screenshot
                screenshot_path = output_dir / page_info['filename']
                await page.screenshot(path=str(screenshot_path), full_page=False)

                # Get file size
                size_kb = screenshot_path.stat().st_size / 1024
                print(f"Saved ({size_kb:.1f} KB)")

            print()
            print("=" * 60)
            print(f"All screenshots saved to {output_dir}/")
            return True

        except Exception as e:
            print(f"\n\nERROR: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure the BCD server is running:")
            print("   python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
            print()
            print("2. Make sure Playwright is installed:")
            print("   pip install playwright")
            print("   playwright install chromium")
            return False

        finally:
            await browser.close()


async def main():
    """Main entry point."""
    success = await take_screenshots()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
