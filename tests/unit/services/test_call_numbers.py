"""Tests for server-side call-number generation used by inventory bulk edits."""

import json

from src.bcd_api.services.catalog.call_numbers import generate_call_number


def test_generate_call_number_applies_rule_and_normalizes_author():
    record = {
        "title": "Le Petit Prince",
        "authors": ["Éric Dupont"],
        "medium_type": "Livre",
        "shelf_location": "Romans",
    }
    rules = [{"shelf_location": "Romans", "pattern": "R {AUT3}"}]

    assert generate_call_number(record, json.dumps(rules)) == "R DUP"


def test_generate_call_number_uses_dewey_and_series_tokens():
    record = {
        "title": "La planète bleue",
        "authors": ["Martin, Sophie"],
        "collection": "Les Explorateurs",
        "dewey_number": "551.46",
        "medium_type": "Livre",
    }
    rules = [{"medium_type": "Livre", "pattern": "{DEWEY} {SER3} {TIT1}"}]

    assert generate_call_number(record, rules) == "551.46 EXP P"


def test_generate_call_number_supports_full_title_token_for_periodicals():
    record = {
        "title": "Les belles histoires",
        "authors": [],
        "medium_type": "Périodique",
    }
    rules = [{"medium_type": "Périodique", "pattern": "PER {TIT}"}]

    assert generate_call_number(record, json.dumps(rules)) == "PER BELLES HISTOIRES"


def test_generate_call_number_empty_matching_pattern_clears_number():
    record = {"title": "Revue", "authors": ["Durand, Ana"], "medium_type": "Périodique"}
    rules = [{"medium_type": "Périodique", "pattern": ""}]

    assert generate_call_number(record, rules) == ""
