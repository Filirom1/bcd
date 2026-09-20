"""Integration tests for the synchronous shelf suggestion model."""

import json
from pathlib import Path

from src.bcd_api.models.bibliographic_record import BibliographicRecord
from src.bcd_api.models.item import Item
from src.bcd_api.services.shelving import suggestion


def _add_labeled_record(db_session, index, shelf, collection):
    record = BibliographicRecord(
        title=f"{collection} title {index}",
        subtitle="A school story",
        authors=json.dumps([f"Author {collection}"]),
        collection=collection,
        medium_type="Livre",
    )
    db_session.add(record)
    db_session.flush()
    db_session.add(
        Item(
            item_id=f"{shelf[:2]}-{index}",
            bibliographic_record_id=record.id,
            shelf_location=shelf,
        )
    )


def test_train_persists_model_and_predicts_top_one(db_session, tmp_path, monkeypatch):
    for index in range(10):
        _add_labeled_record(db_session, index, "Albums", "Albums jeunesse")
        _add_labeled_record(db_session, index, "Romans", "Romans jeunesse")
    db_session.commit()
    monkeypatch.setattr(suggestion, "MODEL_DIR", tmp_path / "models")

    result = suggestion.train(db_session)

    assert result.status == "completed"
    assert result.ready is True
    assert result.trained_on_records == 20
    assert result.model_path is not None
    assert Path(result.model_path).is_file()
    assert (
        suggestion.suggest(
            {
                "title": "Une aventure",
                "subtitle": "A school story",
                "collection": "Albums jeunesse",
                "authors": ["Author Albums jeunesse"],
            },
            suggestion.load_current_model(db_session),
        )
        == "Albums"
    )


def test_train_ignores_shelves_with_fewer_than_ten_notices(db_session, tmp_path, monkeypatch):
    for index in range(9):
        _add_labeled_record(db_session, index, "Albums", "Albums jeunesse")
    db_session.commit()
    monkeypatch.setattr(suggestion, "MODEL_DIR", tmp_path / "models")

    result = suggestion.train(db_session)

    assert result.status == "insufficient_data"
    assert result.ready is False
    assert not (tmp_path / "models").exists()


def test_ambiguous_notice_is_excluded_from_training(db_session, tmp_path, monkeypatch):
    for index in range(10):
        _add_labeled_record(db_session, index, "Albums", "Albums jeunesse")
    ambiguous = BibliographicRecord(
        title="Ambiguous title",
        authors=json.dumps(["Author ambiguous"]),
        collection="Ambiguous",
        medium_type="Livre",
    )
    db_session.add(ambiguous)
    db_session.flush()
    db_session.add_all(
        [
            Item(item_id="amb-a", bibliographic_record_id=ambiguous.id, shelf_location="Albums"),
            Item(item_id="amb-r", bibliographic_record_id=ambiguous.id, shelf_location="Romans"),
        ]
    )
    db_session.commit()
    monkeypatch.setattr(suggestion, "MODEL_DIR", tmp_path / "models")

    result = suggestion.train(db_session)

    assert result.trained_on_records == 10
    assert result.ready is True
