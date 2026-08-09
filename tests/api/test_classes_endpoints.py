from types import SimpleNamespace
import pytest

from src.bcd_api.api.v1 import classes
from src.bcd_api.schemas.class_schema import ClassCreate, ClassUpdate


def test_create_class_endpoint(monkeypatch):
    """Test create_class endpoint delegates correctly to class_service."""
    called_args = {}

    def mock_create(db, name, homeroom_teacher, notes, average_age):
        called_args.update({
            "name": name,
            "homeroom_teacher": homeroom_teacher,
            "notes": notes,
            "average_age": average_age
        })
        return SimpleNamespace(
            id=1, name=name, homeroom_teacher=homeroom_teacher, notes=notes, average_age=average_age,
            created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00"
        )

    monkeypatch.setattr(classes.class_commands, "create_class", mock_create)

    req = ClassCreate(name="CM1", homeroom_teacher="M. Dupont", notes="Class Notes", average_age=9)
    result = classes.create_class(req, db=object())

    assert called_args["name"] == "CM1"
    assert called_args["homeroom_teacher"] == "M. Dupont"
    assert result.id == 1
    assert result.name == "CM1"


def test_get_class_endpoint(monkeypatch):
    """Test get_class endpoint."""
    monkeypatch.setattr(classes.class_queries, "get_class_by_id", lambda db, cid: SimpleNamespace(
        id=cid, name="CP", homeroom_teacher="Mme. Alice", notes=None, average_age=6.0,
        created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00"
    ))

    result = classes.get_class(10, db=object())
    assert result.id == 10
    assert result.name == "CP"


def test_list_classes_endpoint(monkeypatch):
    """Test list_classes endpoint."""
    called = []
    monkeypatch.setattr(classes.class_queries, "list_classes", lambda db, limit, offset: called.append((limit, offset)) or [
        SimpleNamespace(id=1, name="CP", homeroom_teacher="Mme. Alice", notes=None, average_age=6.0,
                        created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00")
    ])

    result = classes.list_classes(limit=50, offset=10, db=object())
    assert called == [(50, 10)]
    assert len(result) == 1
    assert result[0].name == "CP"


def test_update_class_endpoint(monkeypatch):
    """Test update_class endpoint."""
    called = []
    monkeypatch.setattr(classes.class_commands, "update_class", lambda db, class_id, name, homeroom_teacher, notes, average_age: called.append((class_id, name)) or SimpleNamespace(
        id=class_id, name=name, homeroom_teacher=homeroom_teacher, notes=notes, average_age=average_age,
        created_at="2025-01-01T00:00:00", updated_at="2025-01-01T00:00:00"
    ))

    req = ClassUpdate(name="CE1", homeroom_teacher="M. Jean")
    result = classes.update_class(2, req, db=object())

    assert called == [(2, "CE1")]
    assert result.name == "CE1"
    assert result.homeroom_teacher == "M. Jean"


def test_delete_class_endpoint(monkeypatch):
    """Test delete_class endpoint."""
    called = []
    monkeypatch.setattr(classes.class_commands, "delete_class_with_unassignment", lambda db, cid: called.append(cid))

    result = classes.delete_class(3, db=object())
    assert result is None
    assert called == [3]
