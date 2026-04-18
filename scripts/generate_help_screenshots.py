#!/usr/bin/env python3
"""
Generate help screenshots for BCD contextual help panels.

Captures the 30 screenshots referenced by the help markdown files.
Screenshots use realistic data from the database.

Usage:
    python scripts/generate_help_screenshots.py [--base-url URL] [--db-path PATH]

Requirements:
    - BCD server must be running (default: http://127.0.0.1:8000)
    - Run `python scripts/reset_and_simulate.py` first for realistic data
    - Playwright must be installed: pip install playwright && playwright install chromium

Output:
    Screenshots saved to docs/help/images/ (overwritten without confirmation)
    Exit code: 0 if all captures succeeded, 1 if any failed
"""

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

from playwright.async_api import async_playwright


def get_demo_data(db_path: str) -> dict:
    """Query the DB for real IDs needed to drive interactive screenshots."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    today_str = __import__('datetime').date.today().isoformat()

    data = {}

    # Active borrower with current loans
    row = con.execute("""
        SELECT b.borrower_id
        FROM borrower b
        JOIN circulation_transaction c ON c.borrower_id = b.id
        WHERE b.active = 1 AND c.return_date IS NULL
        GROUP BY b.id HAVING COUNT(*) >= 1
        ORDER BY COUNT(*) DESC LIMIT 1
    """).fetchone()
    data["active_borrower_id"] = row["borrower_id"] if row else None

    # Borrower with an overdue loan
    row = con.execute("""
        SELECT b.borrower_id
        FROM borrower b
        JOIN circulation_transaction c ON c.borrower_id = b.id
        WHERE b.active = 1 AND c.return_date IS NULL AND c.due_date < ?
        LIMIT 1
    """, (today_str,)).fetchone()
    data["overdue_borrower_id"] = row["borrower_id"] if row else data.get("active_borrower_id")

    # Borrower suitable for live checkout demo: active, has loans, NO overdue items
    # (BCD blocks checkout for borrowers with overdue items, so this borrower
    # must be clean to ensure the checkout-03 scan succeeds)
    row = con.execute("""
        SELECT b.borrower_id
        FROM borrower b
        WHERE b.active = 1
        AND b.role = 'student'
        AND NOT EXISTS (
            SELECT 1 FROM circulation_transaction c
            WHERE c.borrower_id = b.id AND c.return_date IS NULL AND c.due_date < ?
        )
        AND EXISTS (
            SELECT 1 FROM circulation_transaction c
            WHERE c.borrower_id = b.id AND c.return_date IS NULL
        )
        LIMIT 1
    """, (today_str,)).fetchone()
    data["checkout_borrower_id"] = row["borrower_id"] if row else data.get("active_borrower_id")

    # Blocked borrower
    row = con.execute("""
        SELECT borrower_id FROM borrower
        WHERE active = 0 AND blocked_reason IS NOT NULL LIMIT 1
    """).fetchone()
    data["blocked_borrower_id"] = row["borrower_id"] if row else None

    # Available item barcode — must not be reserved (active hold) for anyone
    row = con.execute("""
        SELECT i.item_id FROM item i
        WHERE i.status = 'available' AND i.loanable = 1
        AND NOT EXISTS (
            SELECT 1 FROM hold h
            WHERE h.bibliographic_record_id = i.bibliographic_record_id
            AND h.status IN ('waiting', 'ready')
        )
        LIMIT 1
    """).fetchone()
    data["available_item_barcode"] = row["item_id"] if row else None

    # Bibliographic record ID with at least one on-loan copy
    row = con.execute("""
        SELECT bibliographic_record_id FROM item WHERE status = 'on_loan' LIMIT 1
    """).fetchone()
    data["detail_record_id"] = str(row["bibliographic_record_id"]) if row else "1"

    # An on-loan item barcode (for return demonstration)
    row = con.execute("""
        SELECT item_id FROM item WHERE status = 'on_loan' LIMIT 1
    """).fetchone()
    data["on_loan_item_barcode"] = row["item_id"] if row else None

    # A book title for catalog search
    row = con.execute("""
        SELECT title FROM bibliographic_record
        WHERE title IS NOT NULL AND title != ''
        ORDER BY RANDOM() LIMIT 1
    """).fetchone()
    data["sample_book_title"] = row["title"][:15] if row else "Harry"

    con.close()
    return data


async def capture_screenshots(base_url: str, demo: dict, output_dir: Path) -> tuple:
    """
    Capture all 30 help screenshots.

    Returns (successes, failures).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    successes = 0
    failures = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="fr-FR",
        )
        page = await context.new_page()
        page.set_default_timeout(5000)

        # ── Verify server is available ────────────────────────────────
        print(f"Checking server at {base_url} ...")
        try:
            response = await page.goto(base_url, wait_until="networkidle", timeout=8000)
            if not response or response.status != 200:
                status = response.status if response else "no response"
                print(f"Server not reachable — HTTP {status}")
                print(f"\nStart the server first:")
                print(f"  python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
                await browser.close()
                return 0, 1
        except Exception as e:
            print(f"Server not reachable — {e}")
            print(f"\nStart the server first:")
            print(f"  python -m uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
            await browser.close()
            return 0, 1

        print("Server is running")
        print()

        def url(path):
            return f"{base_url}/#/{path.lstrip('/')}"

        async def navigate(path, wait_selector=None):
            """Navigate to a page and wait for it to load."""
            await page.goto(url(path), wait_until="networkidle")
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=5000)
                except Exception:
                    pass
            await page.wait_for_timeout(600)

        async def shoot(filename, refresh_after=True):
            """Take a screenshot of the current page, then refresh to clear modals."""
            nonlocal successes, failures
            print(f"  {filename} ...", end=" ", flush=True)
            try:
                path = output_dir / filename
                await page.screenshot(path=str(path), full_page=False)
                size_kb = path.stat().st_size / 1024
                print(f"OK ({size_kb:.0f} KB)")
                successes += 1
                # Refresh page after screenshot to clear any modals or transient state
                if refresh_after:
                    await page.reload(wait_until="networkidle")
                    await page.wait_for_timeout(400)
            except Exception as e:
                print(f"FAILED — {e}")
                failures += 1

        borrower_id   = demo.get("active_borrower_id") or ""
        # checkout_id: borrower without overdue items so the scan in checkout-03
        # succeeds (BCD blocks checkout for borrowers with overdue loans).
        # Must be a pure numeric string to pass ClassRosterPanel's couldBeId check.
        checkout_id   = demo.get("checkout_borrower_id") or borrower_id
        blocked_id    = demo.get("blocked_borrower_id") or borrower_id
        item_bc       = demo.get("available_item_barcode") or ""
        on_loan_bc    = demo.get("on_loan_item_barcode") or item_bc
        rec_id        = demo.get("detail_record_id") or "1"
        book_title    = demo.get("sample_book_title") or ""

        # ── Checkout ─────────────────────────────────────────────────
        await navigate("checkout", ".checkout-page")
        await shoot("checkout-01-empty.png")

        # checkout-02: type numeric student ID → ClassRosterPanel fetches borrower
        # page.type() sends real keydown/input events needed by Vue's @input handler;
        # the numeric ID passes the couldBeId check and triggers the API lookup.
        await navigate("checkout", ".checkout-page")
        try:
            await page.wait_for_timeout(600)  # let classes finish loading
            await page.click("input.filter-input")
            await page.type("input.filter-input", checkout_id, delay=80)
            # Wait for 300 ms debounce + API call + Vue re-render
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await shoot("checkout-02-borrower-loaded.png", refresh_after=False)

        # checkout-03: scan an available item barcode (borrower still loaded from above)
        try:
            await page.click('input[placeholder*="code-barres"]')
            await page.type('input[placeholder*="code-barres"]', item_bc, delay=50)
            await page.wait_for_timeout(400)
            # Click the Emprunter button to submit the checkout
            await page.click("button.btn-success", timeout=3000)
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await shoot("checkout-03-item-scanned.png", refresh_after=False)

        # checkout-04: same state after confirmation (item now in the loans list)
        await shoot("checkout-04-confirmed.png")

        # ── Return ───────────────────────────────────────────────────
        await navigate("return", ".return-page")
        await shoot("return-01-empty.png")

        # return-02: type on-loan item barcode then click Retourner button
        # page.type() sends real keystrokes so Vue's @input handler fires correctly
        try:
            await page.click('input[placeholder*="code-barres"]')
            await page.type('input[placeholder*="code-barres"]', on_loan_bc, delay=50)
            await page.wait_for_timeout(400)
            await page.click("button.btn-info", timeout=3000)
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        await shoot("return-02-item-returned.png")

        # ── Catalog ──────────────────────────────────────────────────
        await navigate("catalog", ".catalog-page")
        await shoot("catalog-01-search.png")

        # For catalog-02: clear the default "Emprunts en cours" filter first so the
        # search finds results from the full catalog, then type the search term.
        try:
            await page.evaluate("""
                () => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const btn = btns.find(b => b.textContent.includes('Effacer')
                                             || b.textContent.includes('Clear'));
                    if (btn) btn.click();
                }
            """)
            await page.wait_for_timeout(600)  # let filter clear and list reload
        except Exception:
            pass
        try:
            await page.fill('input[placeholder*="auteur"]', book_title)
            await page.wait_for_timeout(1500)  # debounce (300 ms) + API call + render
        except Exception:
            pass
        await shoot("catalog-02-results.png")

        await navigate(f"catalog/{rec_id}", ".catalog-page")
        await shoot("catalog-03-detail.png")

        # ── Cataloging ───────────────────────────────────────────────
        await navigate("cataloging", ".cataloging-page")
        await shoot("cataloging-01-isbn.png")

        # cataloging-02: fill ISBN via JS (triggers v-model), then click manual entry
        # to show the bibliographic form with the ISBN pre-filled.
        # Using page.evaluate() to bypass Playwright selector engine issues.
        try:
            await page.evaluate("""
                () => {
                    const input = document.getElementById('isbn-input');
                    if (!input) return;
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, '9782070612758');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            """)
            await page.wait_for_timeout(300)
            await page.evaluate("""
                () => {
                    const btn = document.querySelector('button.btn-link');
                    if (btn) btn.click();
                }
            """)
            await page.wait_for_timeout(800)
        except Exception:
            pass
        await shoot("cataloging-02-form.png")

        # cataloging-03: force component remount by navigating to a different route first,
        # then back to cataloging. Without this, Vue Router skips the remount and state
        # from cataloging-02 (bibliographic-form) would carry over.
        await navigate("catalog", ".catalog-page")
        await navigate("cataloging", ".cataloging-page")
        try:
            await page.evaluate("""
                () => {
                    const btn = document.querySelector('button.btn-link');
                    if (btn) btn.click();
                }
            """)
            await page.wait_for_timeout(800)
        except Exception:
            pass
        await shoot("cataloging-03-manual.png")

        # cataloging-04: force remount again, then submit the ISBN lookup form.
        # If the ISBN is already in the local DB, existing-record-found fires immediately
        # and state goes to item-creation (barcode scan step) — no BNF network call needed.
        await navigate("catalog", ".catalog-page")
        await navigate("cataloging", ".cataloging-page")
        try:
            await page.evaluate("""
                () => {
                    const input = document.getElementById('isbn-input');
                    if (!input) return;
                    const setter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, '9782070612758');
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            """)
            await page.wait_for_timeout(300)
            await page.evaluate("""
                () => {
                    const btn = document.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                }
            """)
            await page.wait_for_timeout(3000)  # DB lookup is fast; no BNF call needed
        except Exception:
            pass
        await shoot("cataloging-04-barcode.png")

        # ── Borrowers ────────────────────────────────────────────────
        await navigate("borrowers", ".borrowers-page")
        await shoot("borrowers-01-list.png")

        await navigate(f"borrowers/{borrower_id}", ".borrowers-page")
        await shoot("borrowers-02-detail.png")

        await navigate(f"borrowers/{blocked_id}", ".borrowers-page")
        await shoot("borrowers-03-block.png")

        await navigate("borrowers", ".borrowers-page")
        try:
            # Click the Admin dropdown button to open the Bootstrap dropdown
            await page.click('[data-testid="admin-dropdown-button"]', timeout=4000)
            await page.wait_for_timeout(500)  # let Bootstrap open the dropdown
            # Click the Import menu item (no :visible check — dropdown may still be animating)
            await page.click('[data-testid="admin-menu-import"]', timeout=3000)
            # Wait for Bootstrap modal animation to complete
            await page.wait_for_timeout(1200)
        except Exception:
            # Fallback: open modal directly via Bootstrap JS API
            try:
                await page.evaluate("""
                    () => {
                        const el = document.getElementById('borrowerImportModal');
                        if (el && window.bootstrap) {
                            new window.bootstrap.Modal(el).show();
                        }
                    }
                """)
                await page.wait_for_timeout(1000)
            except Exception:
                pass
        await shoot("borrowers-04-import.png")

        # ── Classes ──────────────────────────────────────────────────
        await navigate("classes", ".classes-page")
        await shoot("classes-01-list.png")

        # ── Reports ──────────────────────────────────────────────────
        await navigate("reports", ".reports-page")
        await page.wait_for_timeout(1200)
        await shoot("reports-01-tabs.png")

        await navigate("reports/overdue", ".reports-page")
        await page.wait_for_timeout(1200)
        await shoot("reports-02-overdue.png")

        await navigate("reports/most-borrowed", ".reports-page")
        await page.wait_for_timeout(1200)
        await shoot("reports-03-print.png")

        # CREW Weeding report - Never Borrowed method
        await navigate("reports/crew", ".reports-page")
        await page.wait_for_timeout(1500)
        await shoot("reports-04-crew-method.png")

        # CREW report with results showing scores
        try:
            # Let the report load results
            await page.wait_for_timeout(2000)
        except Exception:
            pass
        await shoot("reports-05-crew-results.png")

        # ── Inventory ────────────────────────────────────────────────
        await navigate("inventory", ".inventory-page")
        await page.wait_for_timeout(1200)
        await shoot("inventory-01-scan.png")

        # Switch to Search tab
        try:
            await page.click('button[data-bs-target="#search-tab"]', timeout=3000)
            await page.wait_for_timeout(800)
        except Exception:
            pass
        await shoot("inventory-02-search.png")

        # ── Settings ─────────────────────────────────────────────────
        await navigate("settings", ".settings-page")
        await shoot("settings-01-main.png")

        # ── Collections ──────────────────────────────────────────
        await navigate("collections", ".container-fluid")
        await page.wait_for_timeout(1200)  # let mDNS discovery complete
        await shoot("collections-01-local.png")

        # collections-02: same page, shows network peers if any are discovered
        # (in most cases this will be the same as 01, unless multiple BCD instances
        # are running on the network during screenshot generation)
        await shoot("collections-02-network.png")

        await browser.close()

    return successes, failures


def main():
    parser = argparse.ArgumentParser(
        description="Generate help panel screenshots for BCD contextual help.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_help_screenshots.py
  python scripts/generate_help_screenshots.py --base-url http://127.0.0.1:8080
  python scripts/generate_help_screenshots.py --db-path /path/to/custom.db
        """,
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running BCD server (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to the SQLite database (default: data/bcd.db relative to project root)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    db_path = args.db_path or str(project_root / "data" / "bcd.db")
    output_dir = project_root / "docs" / "help" / "images"

    print("=" * 60)
    print("BCD Help Screenshot Generator")
    print("=" * 60)
    print(f"Server:     {args.base_url}")
    print(f"Database:   {db_path}")
    print(f"Output dir: {output_dir}")
    print()

    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        print("Run `python scripts/reset_and_simulate.py` first.")
        sys.exit(1)

    print("Querying database for demo data IDs ...")
    demo = get_demo_data(db_path)
    for key, val in demo.items():
        print(f"  {key}: {val}")
    print()

    print("Capturing screenshots ...")
    successes, failures = asyncio.run(capture_screenshots(args.base_url, demo, output_dir))

    print()
    print("=" * 60)
    print(f"Done: {successes} succeeded, {failures} failed")
    print(f"Output: {output_dir}/")
    print("=" * 60)

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
