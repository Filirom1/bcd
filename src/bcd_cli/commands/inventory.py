"""Apply prepared inventory groups through the BCD inventory API."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import click

from ..client import get_client
from ..utils.display import console, print_header

REQUIRED_COLUMNS = ("item_id", "shelf_location", "call_number")
GROUPED_FILE_GLOB = "*__*.csv"
BATCH_SIZE = 500


class InventoryInputError(ValueError):
    """Raised when an inventory CSV is invalid."""


@dataclass(frozen=True)
class GroupedInventoryFile:
    """Validated representation of one prepared group."""

    path: Path
    item_ids: tuple[str, ...]
    shelf_location: str
    call_number: str
    medium_type: str | None = None
    loanable: bool | None = None


def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise InventoryInputError(f"{path}: cannot read file: {exc}") from exc

    if not raw.startswith(b"\xef\xbb\xbf"):
        raise InventoryInputError(f"{path}: CSV must be encoded as UTF-8 with BOM")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InventoryInputError(f"{path}: file is not valid UTF-8") from exc

    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        fieldnames = [field.strip() for field in (reader.fieldnames or [])]
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing:
            raise InventoryInputError(f"{path}: required columns missing: {', '.join(missing)}")
        if len(fieldnames) != len(set(fieldnames)):
            raise InventoryInputError(f"{path}: header contains duplicate columns")
        rows = tuple(
            {key.strip(): (value or "").strip() for key, value in row.items() if key is not None}
            for row in reader
        )
    except csv.Error as exc:
        raise InventoryInputError(f"{path}: invalid CSV: {exc}") from exc

    if not rows:
        raise InventoryInputError(f"{path}: group is empty")
    return rows


def read_grouped_csv(path: Path) -> GroupedInventoryFile:
    """Validate one already-grouped CSV without changing its values."""
    rows = _read_rows(path)
    item_ids = tuple(row.get("item_id", "") for row in rows)
    if any(not item_id for item_id in item_ids):
        raise InventoryInputError(f"{path}: an item_id is empty")

    duplicates = sorted({item_id for item_id in item_ids if item_ids.count(item_id) > 1})
    if duplicates:
        raise InventoryInputError(f"{path}: duplicate item_id(s): {', '.join(duplicates[:10])}")

    shelf_values = {row.get("shelf_location", "") for row in rows}
    call_values = {row.get("call_number", "") for row in rows}
    medium_values = {row.get("medium_type", "") for row in rows}
    loanable_values = {row.get("loanable", "") for row in rows}
    if len(shelf_values) != 1:
        raise InventoryInputError(f"{path}: multiple shelf_location values in one group")
    if len(call_values) != 1:
        raise InventoryInputError(f"{path}: multiple call_number values in one group")
    if len(medium_values) != 1:
        raise InventoryInputError(f"{path}: multiple medium_type values in one group")
    if len(loanable_values) != 1:
        raise InventoryInputError(f"{path}: multiple loanable values in one group")
    loanable_value = next(iter(loanable_values))
    if loanable_value.lower() not in {"", "true", "false"}:
        raise InventoryInputError(f"{path}: loanable must be true or false")

    return GroupedInventoryFile(
        path=path,
        item_ids=item_ids,
        shelf_location=next(iter(shelf_values)),
        call_number=next(iter(call_values)),
        medium_type=next(iter(medium_values)) or None,
        loanable=None if not loanable_value else loanable_value.lower() == "true",
    )


def _csv_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".csv":
            raise InventoryInputError(f"{path}: expected a CSV file")
        return [path]
    if not path.is_dir():
        raise InventoryInputError(f"{path}: path does not exist or is not supported")
    # Prepared groups are the only CSVs whose names contain the group marker
    # ``__`` (for example ``001__ALBUMS__A_A.csv``). This intentionally excludes
    # MANIFEST.csv, ABSENTS.csv, A_REVOIR.csv and other control files without a
    # group marker, without maintaining a fragile deny-list.
    return sorted(file for file in path.glob(GROUPED_FILE_GLOB) if file.is_file())


def collect_grouped_files(path: Path) -> list[GroupedInventoryFile]:
    """Validate every visible CSV before making any API request."""
    files = _csv_files(path)
    if not files:
        raise InventoryInputError(f"{path}: no visible CSV files to process")

    groups = [read_grouped_csv(file) for file in files]
    all_ids = [item_id for group in groups for item_id in group.item_ids]
    duplicates = sorted({item_id for item_id in all_ids if all_ids.count(item_id) > 1})
    if duplicates:
        raise InventoryInputError(
            "item_id appears in multiple grouped CSV files: " + ", ".join(duplicates[:10])
        )
    return groups


def _chunks(values: Iterable[str], size: int = BATCH_SIZE) -> Iterable[list[str]]:
    batch: list[str] = []
    for value in values:
        batch.append(value)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _post_json(client: Any, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(endpoint, json=payload)
    if response.status_code < 200 or response.status_code >= 300:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = getattr(response, "text", "unknown response")
        raise RuntimeError(f"{endpoint} ({response.status_code}): {detail}")
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"{endpoint}: API returned an unexpected response")
    return data


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _default_report_path(path: Path) -> Path:
    return (
        path / "inventory-apply-report.json" if path.is_dir() else path.with_suffix(".report.json")
    )


@click.group(name="inventory")
def inventory():
    """Inventory commands."""


@inventory.command(name="delete-orphan-records")
@click.option("--api-url", default="http://localhost:8888", envvar="BCD_API_URL")
@click.option("--dry-run", is_flag=True, help="Display orphan records without modifying BCD")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip confirmation")
@click.option("--report", "report_path", type=click.Path(path_type=Path))
def delete_orphan_records(api_url: str, dry_run: bool, assume_yes: bool, report_path: Path | None):
    """Delete bibliographic records with no remaining physical items."""
    client = get_client(base_url=api_url)
    response = client.get("/api/v1/admin/catalog/orphan-records")
    if response.status_code < 200 or response.status_code >= 300:
        raise click.ClickException(
            f"Unable to list orphan records ({response.status_code}): {response.text}"
        )
    try:
        data = response.json()
        count = int(data.get("count", 0))
    except Exception as exc:
        raise click.ClickException("Orphan-record search returned invalid JSON") from exc

    print_header("Delete orphan records")
    console.print(f"[yellow]Orphan records:[/yellow] {count:,}")
    report_path = report_path or Path("inventory-delete-orphan-records-report.json")
    report: dict[str, Any] = {"orphan_records_found": count, "records_deleted": 0, "errors": []}
    if dry_run or count == 0:
        report["dry_run"] = dry_run
        _write_report(report_path, report)
        console.print(f"[green]No deletion request sent.[/green] Report: {report_path}")
        return
    if not assume_yes and not click.confirm("Delete orphan records from BCD?", default=False):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    response = client.delete("/api/v1/admin/catalog/orphan-records")
    if response.status_code < 200 or response.status_code >= 300:
        report["errors"].append(f"HTTP {response.status_code}: {response.text}")
    else:
        report["records_deleted"] = int(response.json().get("records_deleted", 0))
    _write_report(report_path, report)
    console.print(f"[green]Complete.[/green] records deleted: {report['records_deleted']}")
    if report["errors"]:
        raise click.ClickException("Orphan-record deletion detected errors")


@inventory.command(name="delete-not-listed")
@click.argument("known_ids_file", type=click.Path(exists=True, path_type=Path))
@click.option("--api-url", default="http://localhost:8888", envvar="BCD_API_URL")
@click.option("--dry-run", is_flag=True, help="Display items to delete without modifying BCD")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip confirmation")
@click.option("--report", "report_path", type=click.Path(path_type=Path))
def delete_not_listed(
    known_ids_file: Path, api_url: str, dry_run: bool, assume_yes: bool, report_path: Path | None
):
    """Delete BCD items whose IDs are not listed in KNOWN_IDS_FILE.

    KNOWN_IDS_FILE is a UTF-8 text file with one ID per line, or a semicolon
    separated CSV containing an ``item_id`` column. Items with active loans are
    protected by the inventory deletion service and reported as skipped.
    """
    raw = known_ids_file.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise click.ClickException(f"{known_ids_file}: file must be UTF-8") from exc
    if ";" in text.splitlines()[0] if text.splitlines() else False:
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        if "item_id" not in (reader.fieldnames or []):
            raise click.ClickException(f"{known_ids_file}: missing item_id column")
        known_ids = {
            (row.get("item_id") or "").strip().lstrip(".")
            for row in reader
            if (row.get("item_id") or "").strip()
        }
    else:
        known_ids = {line.strip().lstrip(".") for line in text.splitlines() if line.strip()}

    client = get_client(base_url=api_url)
    response = client.get("/api/v1/inventory/items/search", params={"no_limit": True})
    if response.status_code < 200 or response.status_code >= 300:
        raise click.ClickException(
            f"Unable to list inventory items ({response.status_code}): {response.text}"
        )
    try:
        current_ids = {
            str(item["item_id"])
            for item in response.json().get("items", [])
            if item.get("item_id") is not None
        }
    except Exception as exc:
        raise click.ClickException("Inventory search returned invalid JSON") from exc
    ids_to_delete = sorted(current_ids - known_ids)

    print_header("Delete items not listed in inventory")
    console.print(f"[cyan]Known inventory IDs:[/cyan] {len(known_ids):,}")
    console.print(f"[cyan]Items currently in BCD:[/cyan] {len(current_ids):,}")
    console.print(f"[yellow]Items to delete:[/yellow] {len(ids_to_delete):,}")
    if ids_to_delete:
        console.print(f"[dim]First IDs: {', '.join(ids_to_delete[:20])}[/dim]")

    report_path = report_path or Path("inventory-delete-not-listed-report.json")
    report: dict[str, Any] = {
        "known_ids_file": str(known_ids_file),
        "known_ids": len(known_ids),
        "current_ids": len(current_ids),
        "planned_deletion": len(ids_to_delete),
        "deleted": 0,
        "skipped_on_loan": 0,
        "orphan_records_created": 0,
        "errors": [],
    }
    if dry_run or not ids_to_delete:
        report["dry_run"] = dry_run
        _write_report(report_path, report)
        console.print(f"[green]No deletion request sent.[/green] Report: {report_path}")
        return
    if not assume_yes and not click.confirm("Delete these items from BCD?", default=False):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    for batch in _chunks(ids_to_delete):
        try:
            result = client.delete("/api/v1/inventory/items/bulk", json={"item_ids": batch})
            if result.status_code < 200 or result.status_code >= 300:
                raise RuntimeError(f"HTTP {result.status_code}: {result.text}")
            data = result.json()
            report["deleted"] += int(data.get("items_deleted", 0))
            report["skipped_on_loan"] += int(data.get("items_skipped_on_loan", 0))
            report["orphan_records_created"] += int(data.get("orphan_records_created", 0))
        except Exception as exc:
            report["errors"].append(str(exc))
            break
    _write_report(report_path, report)
    console.print(
        f"[green]Complete.[/green] deleted: {report['deleted']}, "
        f"skipped on loan: {report['skipped_on_loan']}, errors: {len(report['errors'])}"
    )
    if report["errors"]:
        raise click.ClickException("Item deletion detected errors")


@inventory.command(name="clear-call-numbers")
@click.option("--api-url", default="http://localhost:8888", envvar="BCD_API_URL")
@click.option("--dry-run", is_flag=True, help="List the call numbers without modifying BCD")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip confirmation")
@click.option("--allow-unknown", is_flag=True, help="Report unknown IDs without failing")
@click.option(
    "--keep-ids-file",
    type=click.Path(exists=True, path_type=Path),
    help="Text file containing item IDs whose call numbers must be preserved",
)
@click.option("--report", "report_path", type=click.Path(path_type=Path))
def clear_call_numbers(
    api_url: str,
    dry_run: bool,
    assume_yes: bool,
    allow_unknown: bool,
    keep_ids_file: Path | None,
    report_path: Path | None,
):
    """Clear every existing item call number through the inventory API."""
    client = get_client(base_url=api_url)
    response = client.get("/api/v1/inventory/items/search", params={"no_limit": True})
    if response.status_code < 200 or response.status_code >= 300:
        raise click.ClickException(
            f"Unable to list inventory items ({response.status_code}): {response.text}"
        )
    try:
        data = response.json()
        items = data.get("items", [])
    except Exception as exc:
        raise click.ClickException("Inventory search returned invalid JSON") from exc
    keep_ids = set()
    if keep_ids_file:
        keep_ids = {
            line.strip().lstrip(".")
            for line in keep_ids_file.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        }
    item_ids = [
        str(item["item_id"])
        for item in items
        if item.get("call_number") and str(item["item_id"]) not in keep_ids
    ]
    print_header("Clear all call numbers")
    console.print(f"[cyan]Existing call numbers:[/cyan] {len(item_ids):,}")

    report_path = report_path or Path("inventory-clear-call-numbers-report.json")
    report: dict[str, Any] = {
        "input": "GET /api/v1/inventory/items/search?no_limit=true",
        "planned": len(item_ids),
        "kept": len(keep_ids),
        "unknown": [],
        "errors": [],
    }
    if dry_run:
        report["dry_run"] = True
        _write_report(report_path, report)
        console.print(f"[green]Dry run complete.[/green] Report: {report_path}")
        return
    if not assume_yes and not click.confirm("Clear all existing call numbers?", default=False):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    for batch in _chunks(item_ids):
        try:
            result = _post_json(
                client,
                "/api/v1/inventory/items/bulk-update",
                {"item_ids": batch, "item_updates": {"call_number": None}},
            )
            report["unknown"].extend(str(item_id) for item_id in result.get("items_not_found", []))
        except Exception as exc:
            report["errors"].append(str(exc))
            break
    report["cleared"] = len(item_ids) - len(report["unknown"])
    _write_report(report_path, report)
    console.print(
        f"[green]Complete.[/green] cleared: {report['cleared']}, "
        f"unknown: {len(report['unknown'])}, errors: {len(report['errors'])}"
    )
    if report["errors"] or (report["unknown"] and not allow_unknown):
        raise click.ClickException("Call-number clearing detected errors or unknown IDs")


@inventory.command(name="apply-grouped")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--api-url", default="http://localhost:8888", envvar="BCD_API_URL")
@click.option("--dry-run", is_flag=True, help="Validate and preview without modifying BCD")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip confirmation")
@click.option("--no-inventory-mark", is_flag=True, help="Do not update last_inventoried_at")
@click.option(
    "--clear-call-numbers-first",
    is_flag=True,
    help="Clear all selected call numbers through the inventory API before applying groups",
)
@click.option(
    "--auto-call-number",
    is_flag=True,
    help="Generate call numbers from the server-side catalog rules instead of CSV values",
)
@click.option(
    "--clear-only",
    is_flag=True,
    help="Only clear the selected call numbers; do not apply locations or mark inventory",
)
@click.option(
    "--clear-empty-call-number",
    is_flag=True,
    help="Clear existing call numbers when the CSV value is empty",
)
@click.option(
    "--allow-unknown",
    is_flag=True,
    help="Keep applying known IDs and report unknown IDs without failing",
)
@click.option(
    "--skip-not-found",
    is_flag=True,
    help="Remove IDs absent from the inventory before sending write requests",
)
@click.option("--report", "report_path", type=click.Path(path_type=Path))
def apply_grouped(
    input_path: Path,
    api_url: str,
    dry_run: bool,
    assume_yes: bool,
    no_inventory_mark: bool,
    clear_call_numbers_first: bool,
    auto_call_number: bool,
    clear_only: bool,
    clear_empty_call_number: bool,
    allow_unknown: bool,
    skip_not_found: bool,
    report_path: Path | None,
):
    """Apply already-grouped CSV files without regrouping their rows."""
    try:
        groups = collect_grouped_files(input_path)
    except InventoryInputError as exc:
        raise click.ClickException(str(exc)) from exc

    report_path = report_path or _default_report_path(input_path)
    total_items = sum(len(group.item_ids) for group in groups)
    print_header("Apply grouped inventory")
    console.print(f"[cyan]Groups:[/cyan] {len(groups)}")
    console.print(f"[cyan]Items:[/cyan] {total_items:,}")
    for group in groups:
        console.print(
            f"[cyan]{group.path.name}[/cyan] — "
            f"{group.shelf_location or '(empty shelf)'} / "
            f"{group.call_number or '(no call number)'} — {len(group.item_ids)} item(s)"
        )

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "dry_run": dry_run,
        "groups": [
            {
                "file": group.path.name,
                "items": len(group.item_ids),
                "shelf_location": group.shelf_location,
                "call_number": group.call_number,
            }
            for group in groups
        ],
        "unknown": [],
        "errors": [],
        "cleared_call_numbers": 0,
    }

    if dry_run:
        report["summary"] = {"planned": total_items, "applied": 0, "unknown": 0, "errors": 0}
        _write_report(report_path, report)
        console.print(f"\n[green]Dry run complete.[/green] Report: {report_path}")
        return

    if not assume_yes and not click.confirm("Apply these changes to BCD?", default=False):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    client = get_client(base_url=api_url)
    unknown_ids: set[str] = set()
    applied = 0

    if skip_not_found:
        inventory_response = client.get("/api/v1/inventory/items/search", params={"no_limit": True})
        if inventory_response.status_code < 200 or inventory_response.status_code >= 300:
            raise click.ClickException(
                f"Unable to list inventory items ({inventory_response.status_code}): "
                f"{inventory_response.text}"
            )
        try:
            known_ids = {
                str(item["item_id"])
                for item in inventory_response.json().get("items", [])
                if item.get("item_id") is not None
            }
        except Exception as exc:
            raise click.ClickException("Inventory search returned invalid JSON") from exc
        original_ids = {item_id for group in groups for item_id in group.item_ids}
        unknown_ids.update(original_ids - known_ids)
        groups = [
            GroupedInventoryFile(
                path=group.path,
                item_ids=tuple(item_id for item_id in group.item_ids if item_id in known_ids),
                shelf_location=group.shelf_location,
                call_number=group.call_number,
                medium_type=group.medium_type,
                loanable=group.loanable,
            )
            for group in groups
            if any(item_id in known_ids for item_id in group.item_ids)
        ]

    if clear_only:
        clear_call_numbers_first = True

    if clear_call_numbers_first:
        for batch in _chunks(item_id for group in groups for item_id in group.item_ids):
            try:
                data = _post_json(
                    client,
                    "/api/v1/inventory/items/bulk-update",
                    {"item_ids": batch, "item_updates": {"call_number": None}},
                )
                cleared = len(batch) - len(
                    {str(item_id) for item_id in data.get("items_not_found", [])}
                )
                report["cleared_call_numbers"] += cleared
                unknown_ids.update(str(item_id) for item_id in data.get("items_not_found", []))
            except Exception as exc:
                report["errors"].append({"operation": "clear-call-numbers", "error": str(exc)})
                break

    if clear_only:
        report["unknown"] = sorted(unknown_ids)
        report["summary"] = {
            "planned": total_items,
            "applied": 0,
            "unknown": len(unknown_ids),
            "skipped_not_found": len(unknown_ids) if skip_not_found else 0,
            "errors": len(report["errors"]),
            "cleared_call_numbers": report["cleared_call_numbers"],
        }
        _write_report(report_path, report)
        console.print(
            f"\\n[green]Call numbers cleared.[/green] "
            f"cleared: {report['cleared_call_numbers']}, unknown: {len(unknown_ids)}"
        )
        if report["errors"] or (unknown_ids and not (allow_unknown or skip_not_found)):
            raise click.ClickException("Call-number clearing detected errors or unknown item IDs")
        return

    if not report["errors"] and not no_inventory_mark:
        for batch in _chunks(item_id for group in groups for item_id in group.item_ids):
            try:
                data = _post_json(client, "/api/v1/inventory/items/bulk-mark", {"item_ids": batch})
                unknown_ids.update(str(item_id) for item_id in data.get("items_not_found", []))
            except Exception as exc:
                report["errors"].append({"operation": "bulk-mark", "error": str(exc)})
                break

    if not report["errors"]:
        for group in groups:
            item_ids = [item_id for item_id in group.item_ids if item_id not in unknown_ids]
            if not item_ids:
                continue
            updates: dict[str, Any] = {"shelf_location": group.shelf_location}
            if group.loanable is not None:
                updates["loanable"] = group.loanable
            if group.call_number and not auto_call_number:
                updates["call_number"] = group.call_number
            elif not group.call_number and clear_empty_call_number:
                updates["call_number"] = None
            payload: dict[str, Any] = {"item_ids": item_ids, "item_updates": updates}
            if group.medium_type:
                payload["record_updates"] = {"medium_type": group.medium_type}
            if auto_call_number:
                payload["auto_call_number"] = True
            try:
                data = _post_json(
                    client,
                    "/api/v1/inventory/items/bulk-update",
                    payload,
                )
                update_unknown = {str(item_id) for item_id in data.get("items_not_found", [])}
                unknown_ids.update(update_unknown)
                applied += len(item_ids) - len(update_unknown)
            except Exception as exc:
                report["errors"].append(
                    {"operation": "bulk-update", "file": group.path.name, "error": str(exc)}
                )
                break

    report["unknown"] = sorted(unknown_ids)
    report["summary"] = {
        "planned": total_items,
        "applied": applied,
        "unknown": len(unknown_ids),
        "skipped_not_found": len(unknown_ids) if skip_not_found else 0,
        "errors": len(report["errors"]),
        "cleared_call_numbers": report["cleared_call_numbers"],
    }
    _write_report(report_path, report)
    console.print(
        f"\n[green]Complete.[/green] applied: {applied}, "
        f"unknown: {len(unknown_ids)}, errors: {len(report['errors'])}"
    )
    console.print(f"[cyan]Report:[/cyan] {report_path}")
    if report["errors"] or (unknown_ids and not (allow_unknown or skip_not_found)):
        raise click.ClickException("Integration detected errors or unknown item IDs")
