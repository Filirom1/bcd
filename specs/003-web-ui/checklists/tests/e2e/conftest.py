"""
Playwright E2E Test Configuration
Provides fixtures for browser testing with FastAPI live server
"""
import pytest
import uvicorn
from multiprocessing import Process
import time
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from bcd_api.main import app


def run_server():
    """Run FastAPI server in subprocess"""
    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="error")


@pytest.fixture(scope="session")
def live_server():
    """
    Start FastAPI server for E2E tests
    Runs on port 8888 to avoid conflicts with dev server
    """
    proc = Process(target=run_server, daemon=True)
    proc.start()
    
    # Wait for server to start
    time.sleep(2)
    
    # Return base URL
    yield "http://localhost:8888"
    
    # Cleanup
    proc.kill()
    proc.join(timeout=5)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Configure browser context for tests
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "fr-FR",
        "timezone_id": "Europe/Paris",
    }


@pytest.fixture
def context(context):
    """
    Configure page context with longer timeout for slower operations
    """
    context.set_default_timeout(10000)  # 10 seconds
    yield context


# Mark all tests in this directory as browser tests
def pytest_collection_modifyitems(items):
    """Add 'browser' marker to all E2E tests"""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.browser)
