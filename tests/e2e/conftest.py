"""
E2E Test Configuration with Best Practices

Key Features:
- Function-scoped database isolation (each test gets clean state)
- Page Object Model support
- Test data factories for flexibility
- Screenshot on failure
- Performance measurement helpers
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# =============================================================================
# Database Fixtures - Function Scoped for Isolation
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture(scope="session")
def base_database():
    """Create base database once per session with migrations."""
    test_db = Path("test_e2e_base.db")

    # Clean up old database
    if test_db.exists():
        test_db.unlink()

    # Run Alembic migrations
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db.absolute()}"
    env["TESTING"] = "true"

    print(f"\n📦 Creating base database: {test_db}")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )

    if result.returncode != 0:
        print(f"❌ Migration failed:\n{result.stderr}")
        pytest.fail("Database migration failed")

    # Create SystemSettings (required)
    from src.bcd_api.models.system_settings import SystemSettings
    engine = create_engine(f"sqlite:///{test_db.absolute()}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    settings = SystemSettings(
        id=1,
        library_name="BCD E2E Test Library",
        loan_duration_days=14,
        loan_limit_default=2,
        loan_limit_teacher=10,
        renewal_limit=2,
        academic_year_current="2024-2025",
        id_format="numeric",
        id_validation_regex=r"^\d{3,6}$",
        language="fr",
        barcode_type="code39"
    )
    db.add(settings)
    db.commit()
    db.close()
    engine.dispose()  # Close all connections

    print("✅ Base database created with SystemSettings")

    yield str(test_db.absolute())

    # Cleanup
    if test_db.exists():
        test_db.unlink()


@pytest.fixture(scope="function")
def test_database(base_database):
    """Create isolated database for each test via copy."""
    # Generate unique database name for this test
    test_db = Path(f"test_e2e_{int(time.time() * 1000)}.db")

    # Copy base database for isolation
    shutil.copy2(base_database, test_db)

    yield str(test_db.absolute())

    # Cleanup
    if test_db.exists():
        test_db.unlink()


@pytest.fixture(scope="function")
def db_session(test_database):
    """Database session for test data setup."""
    engine = create_engine(f"sqlite:///{test_database}")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()  # Close all connections


# =============================================================================
# API Server Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def api_server_port():
    """Get available port for API server."""
    import socket
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture(scope="function")
def api_server(test_database, api_server_port):
    """Start API server with isolated test database."""
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_database}"
    env["VUE_MODE"] = "true"
    env["TESTING"] = "true"

    log_file = open("test_e2e_server.log", "w")
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "src.bcd_api.main:app",
         "--host", "127.0.0.1", "--port", str(api_server_port)],
        env=env,
        stdout=log_file,
        stderr=log_file,
        cwd=PROJECT_ROOT
    )

    # Wait for server to be ready
    import requests
    base_url = f"http://127.0.0.1:{api_server_port}"
    max_retries = 60

    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/api/v1/admin/health", timeout=2)
            if response.status_code == 200:
                break
        except (requests.ConnectionError, requests.Timeout):
            if i == max_retries - 1:
                process.terminate()
                pytest.fail("API server failed to start")
            time.sleep(0.5)

    yield base_url

    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    log_file.close()


@pytest.fixture(scope="function")
def app_url(api_server):
    """Application URL for testing."""
    return api_server


@pytest.fixture(scope="function")
def server_url(api_server):
    """Server URL for tests (avoids conflict with pytest-base-url plugin)."""
    return api_server


# =============================================================================
# Browser Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Browser launch arguments."""
    return {
        "headless": not os.getenv('HEADED', False),
        "args": ['--disable-dev-shm-usage']
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Browser context arguments."""
    return {
        "viewport": {'width': 1920, 'height': 1080},
        "locale": 'fr-FR',
        "record_video_dir": "test-results/videos" if os.getenv('VIDEO', False) else None,
        "record_har_path": None  # Can enable for debugging
    }


@pytest.fixture(scope="session")
def playwright():
    """Playwright instance."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright, browser_type_launch_args):
    """Browser instance (session-scoped for speed)."""
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser, browser_context_args):
    """Browser context (function-scoped for isolation)."""
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context, app_url, request):
    """Page instance with automatic navigation and screenshot on failure."""
    page = context.new_page()

    # Navigate to app
    page.goto(app_url)

    # Wait for Vue app to load
    try:
        page.wait_for_selector('.sidebar', timeout=10000)
    except:
        print("⚠️  Sidebar not found, app may not have loaded")

    yield page

    # Screenshot on failure
    if request.node.rep_call.failed if hasattr(request.node, 'rep_call') else False:
        screenshot_dir = Path("test-results/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshot_dir / f"{request.node.name}.png"
        page.screenshot(path=str(screenshot_path))
        print(f"📸 Screenshot saved: {screenshot_path}")

    page.close()


# =============================================================================
# Pytest Hooks for Better Reporting
# =============================================================================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Store test results for screenshot on failure."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# =============================================================================
# Test Data Factory Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def borrower_factory(db_session):
    """Factory for creating test borrowers."""
    from tests.e2e.fixtures.borrower_factory import BorrowerFactory
    return BorrowerFactory(db_session)


@pytest.fixture(scope="function")
def item_factory(db_session):
    """Factory for creating test items."""
    from tests.e2e.fixtures.item_factory import ItemFactory
    return ItemFactory(db_session)


# =============================================================================
# Page Object Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def circulation_page(page, app_url):
    """Circulation page object."""
    from tests.e2e.page_objects.circulation_page import CirculationPage
    return CirculationPage(page, app_url)


@pytest.fixture(scope="function")
def catalog_page(page, app_url):
    """Catalog page object."""
    from tests.e2e.page_objects.catalog_page import CatalogPage
    return CatalogPage(page, app_url)


@pytest.fixture(scope="function")
def borrowers_page(page, app_url):
    """Borrowers page object."""
    from tests.e2e.page_objects.borrowers_page import BorrowersPage
    return BorrowersPage(page, app_url)


@pytest.fixture(scope="function")
def settings_page(page, app_url):
    """Settings page object."""
    from tests.e2e.page_objects.settings_page import SettingsPage
    return SettingsPage(page, app_url)


@pytest.fixture(scope="function")
def classes_page(page, app_url):
    """Classes page object."""
    from tests.e2e.page_objects.classes_page import ClassesPage
    return ClassesPage(page, app_url)


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def performance_monitor():
    """Helper for measuring performance."""
    from tests.e2e.helpers.performance import PerformanceMonitor
    return PerformanceMonitor()


# =============================================================================
# Session Setup
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    os.environ['VUE_MODE'] = 'true'

    # Create test results directory
    Path("test-results").mkdir(exist_ok=True)

    yield

    # Cleanup
    os.environ.pop('VUE_MODE', None)
