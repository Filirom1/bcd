import asyncio
import threading
from unittest.mock import MagicMock

from fastapi.exceptions import RequestValidationError

from src.bcd_api import main
from src.bcd_api.core.exceptions import ValidationError


def _run_async(coro):
    result = []
    error = []

    def runner():
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result[0]


def test_bcd_exception_handler_returns_structured_response():
    response = _run_async(main.bcd_exception_handler(MagicMock(), ValidationError("bad input")))
    assert response.status_code == 422
    assert response.body


def test_validation_exception_handler_returns_422():
    exc = RequestValidationError([{"type": "missing", "loc": ("body", "title"), "msg": "required", "input": {}}])
    response = _run_async(main.validation_exception_handler(MagicMock(), exc))
    assert response.status_code == 422


def test_startup_library_code_reads_database_settings(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("src.bcd_api.core.database.SessionLocal", lambda: db)
    monkeypatch.setattr("src.bcd_api.services.settings_service.get_settings", lambda session: MagicMock(library_code="BCD"))
    assert main._get_startup_library_code() == "BCD"
    db.close.assert_called_once()
