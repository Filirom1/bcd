"""Tests for applying prepared inventory CSV groups."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from src.bcd_cli.commands.inventory import (
    InventoryInputError,
    collect_grouped_files,
    inventory,
    read_grouped_csv,
)

HEADER = "item_id;shelf_location;call_number;series_name;pictogramme;source_file;source_line\n"


def write_group(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """Write a small grouped CSV in the same format as the prepared data."""
    content = [HEADER]
    content.extend(
        f"{item_id};{shelf};{call_number};;;prepared.txt;{line}\n"
        for line, (item_id, shelf, call_number) in enumerate(rows, start=1)
    )
    path.write_bytes(("\ufeff" + "".join(content)).encode("utf-8"))


def response(payload: dict) -> MagicMock:
    result = MagicMock()
    result.status_code = 200
    result.json.return_value = payload
    return result


def test_read_grouped_csv_validates_group_and_preserves_leading_zeroes(tmp_path):
    path = tmp_path / "001__ALBUMS__A_A.csv"
    write_group(path, [("0007", "Albums", "A A"), ("0042", "Albums", "A A")])

    group = read_grouped_csv(path)

    assert group.item_ids == ("0007", "0042")
    assert group.shelf_location == "Albums"
    assert group.call_number == "A A"


def test_read_grouped_csv_rejects_missing_required_column(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_bytes(b"\xef\xbb\xbfitem_id;shelf_location\n0007;Albums\n")

    try:
        read_grouped_csv(path)
    except InventoryInputError as exc:
        assert "call_number" in str(exc)
    else:
        raise AssertionError("expected an input validation error")


def test_read_grouped_csv_rejects_mixed_shelf_locations(tmp_path):
    path = tmp_path / "bad.csv"
    write_group(path, [("0007", "Albums", "A A"), ("0042", "Romans", "A A")])

    try:
        read_grouped_csv(path)
    except InventoryInputError as exc:
        assert "multiple shelf_location" in str(exc)
    else:
        raise AssertionError("expected an input validation error")


def test_read_grouped_csv_accepts_arbitrary_call_number_values(tmp_path):
    path = tmp_path / "group.csv"
    write_group(path, [("0007", "Contes", "C À générer")])

    group = read_grouped_csv(path)

    assert group.call_number == "C À générer"


def test_collect_grouped_files_rejects_duplicate_ids_across_files(tmp_path):
    write_group(tmp_path / "001__ALBUMS__A_A.csv", [("0007", "Albums", "A A")])
    write_group(tmp_path / "002__ROMANS__R_A.csv", [("0007", "Romans", "R A")])

    try:
        collect_grouped_files(tmp_path)
    except InventoryInputError as exc:
        assert "multiple grouped CSV" in str(exc)
    else:
        raise AssertionError("expected an input validation error")


def test_collect_grouped_files_skips_control_csv_files(tmp_path):
    write_group(tmp_path / "001__ALBUMS__A_A.csv", [("0007", "Albums", "A A")])
    write_group(tmp_path / ".control.csv", [("0099", "Romans", "R A")])
    (tmp_path / "MANIFEST.csv").write_text("fichier_groupe;nombre_exemplaires\n", encoding="utf-8")
    (tmp_path / "A_REVOIR.csv").write_text("item_id;raison\n", encoding="utf-8")
    (tmp_path / "ABSENTS.csv").write_text("item_id;raison\n", encoding="utf-8")
    (tmp_path / "CONFLITS_TRAITES.csv").write_text("item_id;explication\n", encoding="utf-8")

    groups = collect_grouped_files(tmp_path)

    assert len(groups) == 1
    assert groups[0].item_ids == ("0007",)


def test_apply_grouped_dry_run_does_not_call_api_and_writes_report(tmp_path):
    write_group(tmp_path / "001__ALBUMS__A_A.csv", [("0007", "Albums", "A A")])
    report = tmp_path / "report.json"

    with patch("src.bcd_cli.commands.inventory.get_client") as get_client:
        result = CliRunner().invoke(
            inventory,
            ["apply-grouped", str(tmp_path), "--dry-run", "--report", str(report)],
        )

    assert result.exit_code == 0, result.output
    get_client.assert_not_called()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["summary"] == {"planned": 1, "applied": 0, "unknown": 0, "errors": 0}
    assert data["groups"][0]["file"] == "001__ALBUMS__A_A.csv"


def test_apply_grouped_marks_in_batches_and_updates_each_file(tmp_path):
    write_group(tmp_path / "001__ALBUMS__A_A.csv", [("0007", "Albums", "A A")])
    write_group(tmp_path / "002__ROMANS__R_A.csv", [("0042", "Romans", "R A")])
    client = MagicMock()
    client.post.side_effect = [
        response({"items_updated": 2, "items_not_found": [], "timestamp": "now"}),
        response(
            {
                "items_updated": 1,
                "items_not_found": [],
                "items_skipped_on_loan": 0,
                "records_updated": 0,
                "other_copies_affected": 0,
            }
        ),
        response(
            {
                "items_updated": 1,
                "items_not_found": [],
                "items_skipped_on_loan": 0,
                "records_updated": 0,
                "other_copies_affected": 0,
            }
        ),
    ]

    with patch("src.bcd_cli.commands.inventory.get_client", return_value=client):
        result = CliRunner().invoke(
            inventory, ["apply-grouped", str(tmp_path), "--yes", "--no-inventory-mark"]
        )

    assert result.exit_code == 0, result.output
    # --no-inventory-mark means exactly one update request per prepared file.
    assert client.post.call_count == 2
    payloads = [call.kwargs["json"] for call in client.post.call_args_list]
    assert payloads[0] == {
        "item_ids": ["0007"],
        "item_updates": {"shelf_location": "Albums", "call_number": "A A"},
    }
    assert payloads[1]["item_ids"] == ["0042"]


def test_apply_grouped_reports_unknown_ids_and_returns_failure(tmp_path):
    write_group(tmp_path / "001__ALBUMS__A_A.csv", [("0007", "Albums", "A A")])
    client = MagicMock()
    client.post.side_effect = [
        response({"items_updated": 0, "items_not_found": ["0007"], "timestamp": "now"}),
    ]
    report = tmp_path / "report.json"

    with patch("src.bcd_cli.commands.inventory.get_client", return_value=client):
        result = CliRunner().invoke(
            inventory,
            ["apply-grouped", str(tmp_path), "--yes", "--report", str(report)],
        )

    assert result.exit_code != 0
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["unknown"] == ["0007"]
    assert data["summary"]["unknown"] == 1
    assert client.post.call_count == 1


def test_apply_grouped_can_explicitly_clear_empty_call_number(tmp_path):
    write_group(
        tmp_path / "119__BANDES_DESSINEES__SANS_COTE.csv", [("0007", "Bandes dessinées", "")]
    )
    client = MagicMock()
    client.post.return_value = response(
        {
            "items_updated": 1,
            "items_not_found": [],
            "items_skipped_on_loan": 0,
            "records_updated": 0,
            "other_copies_affected": 0,
        }
    )

    with patch("src.bcd_cli.commands.inventory.get_client", return_value=client):
        result = CliRunner().invoke(
            inventory,
            [
                "apply-grouped",
                str(tmp_path),
                "--yes",
                "--no-inventory-mark",
                "--clear-empty-call-number",
            ],
        )

    assert result.exit_code == 0, result.output
    assert client.post.call_args.kwargs["json"]["item_updates"]["call_number"] is None


def test_apply_grouped_clear_only_uses_inventory_api_without_applying_group(tmp_path):
    write_group(tmp_path / "001__ROMAN__A.csv", [("0007", "Roman", "A")])
    client = MagicMock()
    client.post.return_value = response({"items_updated": 1, "items_not_found": []})

    with patch("src.bcd_cli.commands.inventory.get_client", return_value=client):
        result = CliRunner().invoke(
            inventory, ["apply-grouped", str(tmp_path), "--yes", "--clear-only"]
        )

    assert result.exit_code == 0, result.output
    assert client.post.call_count == 1
    assert client.post.call_args.kwargs["json"] == {
        "item_ids": ["0007"],
        "item_updates": {"call_number": None},
    }


def test_apply_grouped_applies_generic_optional_item_and_record_fields(tmp_path):
    path = tmp_path / "001__GROUP.csv"
    path.write_bytes(
        (
            "\ufeffitem_id;shelf_location;call_number;medium_type;loanable\n"
            "0007;Périodique / Astrapi;;Périodique;false\n"
        ).encode("utf-8")
    )
    client = MagicMock()
    client.post.return_value = response(
        {
            "items_updated": 1,
            "items_not_found": [],
            "items_skipped_on_loan": 0,
            "records_updated": 1,
            "other_copies_affected": 0,
        }
    )

    with patch("src.bcd_cli.commands.inventory.get_client", return_value=client):
        result = CliRunner().invoke(
            inventory,
            ["apply-grouped", str(path), "--yes", "--no-inventory-mark"],
        )

    assert result.exit_code == 0, result.output
    payload = client.post.call_args.kwargs["json"]
    assert payload["item_updates"] == {
        "shelf_location": "Périodique / Astrapi",
        "loanable": False,
    }
    assert payload["record_updates"] == {"medium_type": "Périodique"}
