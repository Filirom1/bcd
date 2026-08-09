import asyncio
import threading
from unittest.mock import MagicMock

import pytest
from fastapi.exceptions import RequestValidationError

from src.bcd_api.core import exception_handlers
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
    response = _run_async(exception_handlers.bcd_exception_handler(MagicMock(), ValidationError("bad input")))
    assert response.status_code == 422
    assert response.body


def test_validation_exception_handler_returns_422():
    exc = RequestValidationError([{"type": "missing", "loc": ("body", "title"), "msg": "required", "input": {}}])
    response = _run_async(exception_handlers.validation_exception_handler(MagicMock(), exc))
    assert response.status_code == 422
