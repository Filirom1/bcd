"""Commands for managing BCD application settings."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..client import get_client
from ..utils.display import console, print_header

# These are school configuration data, not translated interface labels.
SHELF_LOCATIONS = [
    {"label": "Documentaires", "color": "#33CC66"},
    {"label": "Album Illustré", "color": "#F2BF33"},
    {"label": "Roman", "color": "#F24D66"},
    {"label": "BD", "color": "#4D99F2"},
    {"label": "Mangas", "color": "#98238B"},
    {"label": "Contes", "color": "#E67E22"},
    {"label": "Dictionnaire", "color": None},
    {"label": "Disney", "color": "#5B4BB7"},
    {"label": "Livre de classe", "color": None},
    {"label": "Livre jeux", "color": "#16A085"},
    {"label": "Livre macdo", "color": "#E74C3C"},
    {"label": "Périodique", "color": "#16A085"},
    {"label": "Poeme", "color": None},
    {"label": "Premiere lecture", "color": "#F39C12"},
    {"label": "Vrac", "color": "#95A5A6"},
]


@click.group(name="settings")
def settings():
    """Manage BCD application settings."""


@settings.command(name="create-locations")
@click.option(
    "--locations-file",
    type=click.Path(exists=True, path_type=Path),
    help="JSON file containing a list of {label, color} shelf locations",
)
@click.option("--api-url", default="http://localhost:8888", envvar="BCD_API_URL")
@click.option("--dry-run", is_flag=True, help="Display the locations without modifying BCD")
@click.option("--yes", "assume_yes", is_flag=True, help="Skip confirmation")
def create_locations(locations_file: Path | None, api_url: str, dry_run: bool, assume_yes: bool):
    """Replace shelf locations from a generic JSON configuration file."""
    locations = SHELF_LOCATIONS
    if locations_file:
        try:
            locations = json.loads(locations_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise click.ClickException(f"Invalid locations file: {locations_file}") from exc
        if not isinstance(locations, list) or not all(
            isinstance(location, dict) and isinstance(location.get("label"), str)
            for location in locations
        ):
            raise click.ClickException(
                "Locations file must contain a JSON list of objects with label"
            )

    print_header("Create shelf locations")
    for location in locations:
        console.print(f"[cyan]-[/cyan] {location['label']}")

    if dry_run:
        console.print("[green]Dry run complete; no API request sent.[/green]")
        return
    if not assume_yes and not click.confirm(
        "Replace the configured shelf locations?", default=False
    ):
        console.print("[yellow]Operation cancelled.[/yellow]")
        return

    client = get_client(base_url=api_url)
    response = client.put(
        "/api/v1/admin/settings",
        json={"updates": {"catalog_shelf_locations": locations}},
    )
    if response.status_code < 200 or response.status_code >= 300:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise click.ClickException(f"Unable to create locations ({response.status_code}): {detail}")
    console.print("[green]Shelf locations created.[/green]")
