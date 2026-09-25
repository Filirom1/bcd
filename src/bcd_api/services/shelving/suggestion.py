"""Pure-Python shelf-location suggestion model.

The model is deliberately small and self contained.  Training is also kept in
this module so that the portable application never needs scikit-learn (or any
of its native dependencies) to train or use a model.
"""

from __future__ import annotations

import collections
import json
import logging
import math
import random
import re
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from sqlalchemy.orm import Session

from ...core.config import settings
from ...models.bibliographic_record import BibliographicRecord
from ...models.item import Item

logger = logging.getLogger(__name__)

FIELDS = ("title", "subtitle", "collection", "authors")
FIELD_WEIGHTS = {"title": 1.1, "subtitle": 0.6, "collection": 2.8, "authors": 2.2}
EXACT_WEIGHTS = {"collection": 3.0, "authors": 2.0}
MIN_EXAMPLES_PER_SHELF = 10
MODEL_DIR = Path("data/models")
_DEFAULT_MODEL_DIR = MODEL_DIR
MODEL_VERSION = "1.0"
SGD_EPOCHS = 3
SGD_LEARNING_RATE = 0.05
SGD_DECAY = 0.0002
# Linear scores are not probabilities.  A small score gap means that the
# model has insufficient discriminating evidence and should abstain.
MIN_SUGGESTION_MARGIN = 0.1

# stopwordsiso provides curated stop-word lists for many languages.  Merge
# every available language so imported catalogues are not biased toward French.
# Normalizing here is important because feature extraction strips accents too.
try:
    from stopwordsiso import languages as _stopword_languages
    from stopwordsiso import stopwords as _language_stopwords
except ImportError:  # Keep source checkouts usable before optional dependencies install.
    _stopword_languages = lambda: ()
    _language_stopwords = lambda _language: ()

STOP_WORDS = {
    "".join(
        char
        for char in unicodedata.normalize("NFD", word)
        if unicodedata.category(char) != "Mn"
    ).casefold()
    for language in _stopword_languages()
    for word in _language_stopwords(language)
}
# A small fallback keeps development/source checkouts functional before pip
# dependencies are installed; installed builds use the complete multilingual set.
if not STOP_WORDS:
    STOP_WORDS = {"a", "an", "and", "the", "de", "des", "et", "la", "le", "les", "un", "une"}

_WORD_SPLIT = re.compile(r"[^\w]+", re.UNICODE)
_TRAIN_LOCK = threading.Lock()
_CURRENT_MODEL: "TrainedModel | None" = None
_CURRENT_MODEL_PATH: str | None = None


@dataclass(frozen=True)
class TrainedModelInfo:
    """Result of a synchronous training operation."""

    model_path: str | None
    trained_at: datetime | None
    trained_on_records: int | None
    ready: bool
    status: str


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").casefold()


def _authors_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value if item)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value
        if isinstance(decoded, list):
            return " ".join(str(item) for item in decoded if item)
    return str(value)


def _field_values(fields: Mapping[str, Any]) -> dict[str, str]:
    return {
        "title": str(fields.get("title") or ""),
        "subtitle": str(fields.get("subtitle") or ""),
        "collection": str(fields.get("collection") or ""),
        "authors": _authors_text(fields.get("authors")),
    }


def _feature_counts(
    fields: Mapping[str, Any], known_terms: set[str] | None = None
) -> dict[str, float]:
    """Extract the same sparse word/character/exact blocks used by inference."""
    values = _field_values(fields)
    counts: dict[str, float] = collections.defaultdict(float)

    def add(key: str) -> None:
        if known_terms is None or key in known_terms:
            counts[key] += 1.0

    for field in FIELDS:
        value = _strip_accents(values[field])
        tokens = [
            token for token in _WORD_SPLIT.split(value) if token and token not in STOP_WORDS
        ]

        for index, token in enumerate(tokens):
            add(f"{field}:w:{token}")
            if index + 1 < len(tokens):
                add(f"{field}:w:{token} {tokens[index + 1]}")
            if index + 2 < len(tokens):
                add(f"{field}:w:{token} {tokens[index + 1]} {tokens[index + 2]}")

        for word in _WORD_SPLIT.split(value):
            if not word:
                continue
            padded = f" {word} "
            for length in range(2, 6):
                for index in range(len(padded) - length + 1):
                    add(f"{field}:c:{padded[index:index + length]}")

    for field in EXACT_WEIGHTS:
        value = values[field].strip().casefold()
        if value:
            add(f"{field}:exact:{value}")

    return dict(counts)


def _block_vector(
    counts: Mapping[str, float],
    idf: Mapping[str, float],
    field: str,
    field_weight: float,
) -> dict[str, float]:
    """Build and L2-normalize one word or character block."""
    prefix = f"{field}:"
    blocks = {"w": {}, "c": {}}
    for key, term_count in counts.items():
        if not key.startswith(prefix) or key.startswith(f"{field}:exact:"):
            continue
        block_type = "c" if key.startswith(f"{field}:c:") else "w"
        value = (1.0 + math.log(term_count)) * idf[key]
        blocks[block_type][key] = value

    result: dict[str, float] = {}
    for block_type, block in blocks.items():
        norm = math.sqrt(sum(value * value for value in block.values())) or 1.0
        weight = field_weight * 0.8 if block_type == "c" else field_weight
        result.update({key: value / norm * weight for key, value in block.items()})
    return result


def _vectorize(
    fields: Mapping[str, Any],
    idf: Mapping[str, float],
    known_terms: set[str],
) -> dict[str, float]:
    counts = _feature_counts(fields, known_terms)
    vector: dict[str, float] = {}
    for field, weight in FIELD_WEIGHTS.items():
        vector.update(_block_vector(counts, idf, field, weight))
    for field, weight in EXACT_WEIGHTS.items():
        key = f"{field}:exact:{_field_values(fields)[field].strip().casefold()}"
        if key in counts:
            vector[key] = weight

    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: value / norm for key, value in vector.items()}


def _record_fields(record: BibliographicRecord) -> dict[str, Any]:
    return {
        "title": record.title,
        "subtitle": record.subtitle,
        "collection": record.collection,
        "authors": record.authors,
    }


def _training_records(db: Session) -> list[tuple[BibliographicRecord, str]]:
    """Return notices having exactly one distinct, non-empty shelf location."""
    rows = (
        db.query(BibliographicRecord, Item.shelf_location)
        .join(Item, Item.bibliographic_record_id == BibliographicRecord.id)
        .filter(Item.shelf_location.isnot(None), Item.shelf_location != "")
        .all()
    )
    shelves_by_record: dict[int, set[str]] = collections.defaultdict(set)
    records_by_id: dict[int, BibliographicRecord] = {}
    for record, shelf in rows:
        records_by_id[record.id] = record
        shelves_by_record[record.id].add(shelf.strip())

    unique = [
        (records_by_id[record_id], next(iter(shelves)))
        for record_id, shelves in shelves_by_record.items()
        if len(shelves) == 1 and next(iter(shelves))
    ]
    return sorted(unique, key=lambda pair: pair[0].id)


def _model_dir() -> Path:
    """Return the configured directory for regenerable model artifacts."""
    # MODEL_DIR remains overridable for tests and callers that monkeypatch it.
    if MODEL_DIR != _DEFAULT_MODEL_DIR:
        return MODEL_DIR
    return Path(settings.models_dir_path) if settings.models_dir_path else MODEL_DIR


def _artifact_path() -> Path:
    """Return the regenerable model path outside SQLite."""
    return _model_dir() / "shelf_suggestion.json"


def _parse_trained_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _read_artifact() -> tuple[Path, dict[str, Any] | None]:
    path = _artifact_path()
    if not path.is_file():
        return path, None
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        logger.warning("Unable to read shelf suggestion model %s", path)
        return path, None


class TrainedModel:
    """Sparse linear model loaded from the JSON artefact."""

    def __init__(self, model_dict: Mapping[str, Any]):
        self.classes = list(model_dict.get("classes", []))
        self.intercepts = [float(value) for value in model_dict.get("intercepts", [])]
        self.terms = model_dict.get("terms", {})
        self.idf = self.terms_idf()
        self.field_weights = model_dict.get("field_weights", FIELD_WEIGHTS)
        self.exact_weights = model_dict.get("exact_weights", EXACT_WEIGHTS)

    def predict(self, fields: Mapping[str, Any]) -> list[tuple[str, float]]:
        if not self.classes:
            return []
        known_terms = set(self.terms)
        values = _field_values(fields)
        counts = _feature_counts(values, known_terms)
        vector: dict[str, float] = {}
        for field, weight in self.field_weights.items():
            vector.update(_block_vector(counts, self.idf, field, float(weight)))
        for field, weight in self.exact_weights.items():
            key = f"{field}:exact:{values[field].strip().casefold()}"
            if key in counts:
                vector[key] = float(weight)

        # Do not classify from class priors alone.  If none of the input
        # metadata terms occurred often enough in the training set, the model
        # has no evidence for a shelf and must let the deterministic caller
        # fallback apply instead.
        if not vector:
            return []

        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        scores = list(self.intercepts)
        for key, raw_value in vector.items():
            entry = self.terms.get(key)
            if not entry:
                continue
            value = raw_value / norm
            for class_index, coefficient in entry.get("c", {}).items():
                index = int(class_index)
                if 0 <= index < len(scores):
                    scores[index] += float(coefficient) * value

        return sorted(zip(self.classes, scores), key=lambda pair: (-pair[1], pair[0]))

    def terms_idf(self) -> dict[str, float]:
        return {key: float(value.get("idf", 1.0)) for key, value in self.terms.items()}

    def suggest(self, fields: Mapping[str, Any]) -> str | None:
        ranked = self.predict(fields)
        if not ranked:
            return None
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < MIN_SUGGESTION_MARGIN:
            return None
        return ranked[0][0]


def _build_model(rows: list[tuple[BibliographicRecord, str]]) -> tuple[dict[str, Any], int]:
    labels = [label for _, label in rows]
    support = collections.Counter(labels)
    supported = {label for label, count in support.items() if count >= MIN_EXAMPLES_PER_SHELF}
    rows = [(record, label) for record, label in rows if label in supported]
    classes = sorted(supported)
    if not rows or not classes:
        return {"version": MODEL_VERSION, "classes": [], "intercepts": [], "terms": {}}, 0

    raw_counts = [_feature_counts(_record_fields(record)) for record, _ in rows]
    document_frequency: collections.Counter[str] = collections.Counter()
    for counts in raw_counts:
        document_frequency.update(counts.keys())

    # Drop terms present in almost every notice.  Exact blocks are retained.
    n_records = len(rows)
    usable_terms = {
        key
        for key, frequency in document_frequency.items()
        if (
            (key.startswith(("collection:exact:", "authors:exact:")) and frequency >= 2)
            or (
                not key.startswith(("collection:exact:", "authors:exact:"))
                and frequency >= 3
                and frequency <= max(1, int(n_records * 0.95))
            )
        )
    }
    idf = {
        key: math.log((1.0 + n_records) / (1.0 + document_frequency[key])) + 1.0
        for key in usable_terms
    }
    class_index = {label: index for index, label in enumerate(classes)}
    vectors = [_vectorize(_record_fields(record), idf, usable_terms) for record, _ in rows]
    targets = [class_index[label] for _, label in rows]
    coefficients: dict[str, list[float]] = {key: [0.0] * len(classes) for key in usable_terms}
    intercepts = [0.0] * len(classes)

    # Deterministic multiclass hinge-loss SGD.  It is intentionally small and
    # sparse: unlike a full optimizer it needs no matrix library at runtime.
    order = list(range(len(rows)))
    rng = random.Random(42)
    step = 0
    for _ in range(SGD_EPOCHS):
        rng.shuffle(order)
        for row_index in order:
            vector = vectors[row_index]
            target = targets[row_index]
            scores = [
                intercepts[class_index_]
                + sum(value * coefficients[key][class_index_] for key, value in vector.items())
                for class_index_ in range(len(classes))
            ]
            competing = max(
                (index for index in range(len(classes)) if index != target),
                key=lambda index: scores[index],
                default=target,
            )
            if scores[target] - scores[competing] >= 1.0:
                continue
            step += 1
            rate = SGD_LEARNING_RATE / (1.0 + SGD_DECAY * step)
            for key, value in vector.items():
                coefficients[key][target] += rate * value
                coefficients[key][competing] -= rate * value
            intercepts[target] += rate
            intercepts[competing] -= rate

    terms: dict[str, dict[str, Any]] = {}
    for key in sorted(usable_terms):
        class_coefficients = {
            str(index): round(value, 7)
            for index, value in enumerate(coefficients[key])
            if abs(value) > 1e-9
        }
        if class_coefficients:
            entry: dict[str, Any] = {"w": 1.0, "c": class_coefficients}
            if ":exact:" not in key:
                entry["idf"] = round(idf[key], 7)
            terms[key] = entry

    model = {
        "version": MODEL_VERSION,
        "classes": classes,
        "intercepts": [round(value, 7) for value in intercepts],
        "terms": terms,
        "field_weights": FIELD_WEIGHTS,
        "exact_weights": EXACT_WEIGHTS,
    }
    return model, n_records


def train(db: Session) -> TrainedModelInfo:
    """Synchronously fit and persist the model using all eligible notices.

    This function intentionally does not schedule a task. The caller remains
    blocked until the JSON artefact is atomically replaced on disk.
    """
    global _CURRENT_MODEL, _CURRENT_MODEL_PATH

    with _TRAIN_LOCK:
        rows = _training_records(db)
        model_dict, record_count = _build_model(rows)
        if not model_dict["classes"]:
            existing = get_status(db)
            return TrainedModelInfo(
                model_path=existing.model_path,
                trained_at=existing.trained_at,
                trained_on_records=existing.trained_on_records,
                ready=existing.ready,
                status="insufficient_data",
            )

        _model_dir().mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc)
        artifact_path = _artifact_path()
        model_dict["trained_at"] = timestamp.isoformat()
        model_dict["trained_on_records"] = record_count
        temporary_path = artifact_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(model_dict, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        # A complete model is always visible to readers; a failed write never
        # leaves a partially written JSON file at the active path.
        temporary_path.replace(artifact_path)

        _CURRENT_MODEL = TrainedModel(model_dict)
        _CURRENT_MODEL_PATH = str(artifact_path)
        return TrainedModelInfo(
            model_path=str(artifact_path),
            trained_at=timestamp,
            trained_on_records=record_count,
            ready=True,
            status="completed",
        )


def load_current_model(db: Session) -> TrainedModel | None:
    """Load the standalone artefact once, returning ``None`` when unavailable."""
    global _CURRENT_MODEL, _CURRENT_MODEL_PATH
    del db  # The artifact location is independent from the database.
    path, model_dict = _read_artifact()
    if model_dict is None:
        return None
    if _CURRENT_MODEL is not None and _CURRENT_MODEL_PATH == str(path):
        return _CURRENT_MODEL

    try:
        model = TrainedModel(model_dict)
    except (TypeError, ValueError, KeyError) as exc:
        logger.warning("Unable to load shelf suggestion model %s: %s", path, exc)
        return None
    _CURRENT_MODEL = model
    _CURRENT_MODEL_PATH = str(path)
    return model


def suggest(fields: Mapping[str, Any], model: TrainedModel | None) -> str | None:
    """Return the Top-1 shelf suggestion for a loaded model."""
    return model.suggest(fields) if model else None


def is_enabled() -> bool:
    """Whether a valid, trained JSON artifact activates suggestions."""
    path, model_dict = _read_artifact()
    del path
    return bool(model_dict and model_dict.get("classes"))


def get_status(db: Session) -> TrainedModelInfo:
    """Return current metadata without performing training."""
    del db  # Status is read from the regenerable artifact, not SQLite.
    path, model_dict = _read_artifact()
    ready = bool(model_dict and model_dict.get("classes"))
    return TrainedModelInfo(
        model_path=str(path) if ready else None,
        trained_at=_parse_trained_at(model_dict.get("trained_at")) if model_dict else None,
        trained_on_records=(model_dict.get("trained_on_records") if model_dict else None),
        ready=ready,
        status="ready" if ready else "not_trained",
    )
