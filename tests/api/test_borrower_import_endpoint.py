from types import SimpleNamespace

import pytest

from bcd_api.api.v1 import borrowers
from bcd_api.core.exceptions import NotFoundError


class Upload:
    def __init__(self, content: bytes):
        self.content = content

    async def read(self):
        return self.content


@pytest.mark.asyncio
async def test_import_borrowers_reports_validation_rows(monkeypatch):
    csv = b"borrower_id,first_name,last_name,role\n,NoId,Name,student\nB2,,Name,student\nB3,First,,student\nB4,First,Name,parent\n"
    result = await borrowers.import_borrowers_csv(Upload(csv), db=object())
    assert result["total_rows"] == 4
    assert result["failed_rows"] == 4
    assert result["successful_rows"] == 0
    assert len(result["errors"]) == 4


@pytest.mark.asyncio
async def test_import_borrowers_creates_and_updates(monkeypatch):
    created = []
    updated = []
    monkeypatch.setattr(borrowers.borrower_service, "get_borrower_by_id", lambda db, value: (_ for _ in ()).throw(NotFoundError("Borrower", value)) if value == "NEW" else SimpleNamespace())
    monkeypatch.setattr(borrowers.borrower_service, "create_borrower", lambda **kwargs: created.append(kwargs))
    monkeypatch.setattr(borrowers.borrower_service, "update_borrower", lambda **kwargs: updated.append(kwargs))
    csv = b"StudentID,FirstName,LastName,Class,Role,Active\nNEW,Zo\xC3\xAB,Nom,CM1,student,oui\nOLD,Alice,Existing,,teacher,false\n"
    result = await borrowers.import_borrowers_csv(Upload(csv), db=object())
    assert result["borrowers_created"] == 1
    assert result["borrowers_updated"] == 1
    assert created[0]["borrower_id"] == "NEW"
    assert updated[0]["active"] is False


@pytest.mark.asyncio
async def test_import_borrowers_accepts_latin1_and_class_creation_failure(monkeypatch):
    monkeypatch.setattr(borrowers.borrower_service, "get_borrower_by_id", lambda *args: (_ for _ in ()).throw(NotFoundError("Borrower", "B1")))
    monkeypatch.setattr(borrowers.borrower_service, "create_borrower", lambda **kwargs: None)
    csv = "StudentID,FirstName,LastName,Class\nB1,Élise,École,CM1\n".encode("latin-1")
    result = await borrowers.import_borrowers_csv(Upload(csv), db=object())
    assert result["successful_rows"] == 1
