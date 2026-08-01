"""
Hold commands

Commands for managing holds/reservations (librarian-mediated).
"""

from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from ..client import get_client
from ..utils.display import console, print_error


@click.group(name="hold")
def hold():
    """Manage holds/reservations."""
    pass


@hold.command(name="add")
@click.argument("borrower_id", required=False)
@click.argument("biblio_id", type=int, required=False)
@click.option(
    "--borrower-id",
    "borrower_id_opt",
    help="Borrower database ID",
)
@click.option(
    "--biblio-id",
    "biblio_id_opt",
    type=int,
    help="Bibliographic record ID",
)
@click.option(
    "--notes",
    help="Additional notes",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def add_hold(
    borrower_id: Optional[str],
    biblio_id: Optional[int],
    borrower_id_opt: Optional[str],
    biblio_id_opt: Optional[int],
    notes: Optional[str],
    api_url: str,
):
    """
    Place a hold/reservation for a bibliographic record.

    \b
    Usage:
        bcd hold add <borrower-id> <biblio-id>
        bcd hold add --borrower-id 1 --biblio-id 42
    """
    try:
        # Use argument or option
        final_borrower_id = borrower_id or borrower_id_opt
        final_biblio_id = biblio_id or biblio_id_opt

        if not final_borrower_id or not final_biblio_id:
            print_error(
                "Both borrower ID and bibliographic record ID are required\n"
                "Usage: bcd hold add <borrower-id> <biblio-id>"
            )
            raise click.Abort()

        client = get_client(base_url=api_url)

        # Get borrower info first
        borrower_response = client.get(f"/api/v1/borrowers/{final_borrower_id}")
        if borrower_response.status_code != 200:
            print_error(f"Borrower not found: {final_borrower_id}")
            raise click.Abort()

        borrower_data = borrower_response.json()

        # Get bibliographic record info
        biblio_response = client.get(f"/api/v1/catalog/bibliographic/{final_biblio_id}")
        if biblio_response.status_code != 200:
            print_error(f"Bibliographic record not found: {final_biblio_id}")
            raise click.Abort()

        biblio_data = biblio_response.json()

        # Display confirmation
        console.print()
        console.print(
            Panel(
                "[bold cyan]📌 Nouvelle réservation / New Hold[/bold cyan]",
                style="cyan"
            )
        )
        console.print()

        console.print(
            f"[bold]Emprunteur / Borrower:[/bold] {borrower_data.get('full_name', 'N/A')} "
            f"(ID: {borrower_data.get('borrower_id', 'N/A')})"
        )
        if borrower_data.get("class_name"):
            console.print(f"[bold]Classe / Class:[/bold] {borrower_data['class_name']}")

        console.print()

        console.print(f"[bold]Notice / Record:[/bold] {biblio_data.get('title', 'N/A')}")
        if biblio_data.get("authors"):
            console.print(f"[bold]Auteur / Author:[/bold] {biblio_data['authors']}")
        console.print(
            f"[bold]Exemplaires / Copies:[/bold] {biblio_data.get('total_items', 0)}"
        )

        # Check how many are available
        items_response = client.get(
            f"/api/v1/catalog/bibliographic/{final_biblio_id}/items"
        )
        if items_response.status_code == 200:
            items = items_response.json()
            available = sum(1 for item in items if item.get("status") == "available")
            console.print(
                f"  [green]→ {available} disponible(s) / available[/green]"
            )

        console.print()

        # Confirm
        if not click.confirm("Créer la réservation ? / Create hold?", default=True):
            console.print("[yellow]Annulé / Cancelled[/yellow]")
            return

        # Create hold
        payload = {
            "borrower_id": int(borrower_data["id"]),  # Use database ID
            "bibliographic_record_id": final_biblio_id,
            "created_by": "cli",
        }
        if notes:
            payload["notes"] = notes

        response = client.post("/api/v1/holds", json=payload)

        if response.status_code == 201:
            hold = response.json()
            console.print()
            console.print("[green]✅ Réservation créée / Hold created[/green]")
            console.print(f"   Hold ID: {hold['id']}")
            console.print(
                f"   Position dans la file / Queue position: {hold['queue_position']}"
            )

            # Estimate availability
            if hold["queue_position"] > 1:
                days_estimate = hold["queue_position"] * 7  # ~7 days per position
                console.print(
                    f"   Disponibilité estimée / Estimated availability: "
                    f"~{days_estimate} jours / days"
                )
        else:
            error_data = response.json() if response.headers.get("content-type", "").startswith(
                "application/json"
            ) else {}
            print_error(f"Error creating hold: {error_data.get('detail', response.text)}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@hold.command(name="list")
@click.argument("borrower_id", required=True)
@click.option(
    "--include-fulfilled",
    is_flag=True,
    help="Include fulfilled/cancelled/expired holds",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def list_holds(borrower_id: str, include_fulfilled: bool, api_url: str):
    """
    List holds for a borrower.

    Args:
        borrower_id: Borrower ID
    """
    try:
        client = get_client(base_url=api_url)

        # Get borrower info
        borrower_response = client.get(f"/api/v1/borrowers/{borrower_id}")
        if borrower_response.status_code != 200:
            print_error(f"Borrower not found: {borrower_id}")
            raise click.Abort()

        borrower_data = borrower_response.json()

        # Get holds
        params = {"include_fulfilled": include_fulfilled}
        response = client.get(
            f"/api/v1/holds/borrower/{borrower_data['id']}", params=params
        )

        if response.status_code == 200:
            holds = response.json()

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold cyan]📌 Réservations / Holds for {borrower_data.get('full_name', 'N/A')}[/bold cyan]",
                    style="cyan"
                )
            )
            console.print()

            if not holds:
                console.print("[dim]Aucune réservation / No holds[/dim]")
                return

            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim")
            table.add_column("Titre\nTitle", style="cyan")
            table.add_column("Pos.", justify="center")
            table.add_column("Statut\nStatus")
            table.add_column("Date")

            for hold in holds:
                status_display = {
                    "waiting": "🟡 En attente",
                    "ready": "🟢 Prêt",
                    "fulfilled": "✅ Retiré",
                    "cancelled": "❌ Annulé",
                    "expired": "⏱️ Expiré",
                }.get(hold.get("status", ""), hold.get("status", ""))

                table.add_row(
                    str(hold["id"]),
                    hold.get("title", "N/A")[:40],
                    str(hold.get("queue_position", "-")),
                    status_display,
                    hold.get("hold_date", "N/A")[:10],
                )

            console.print(table)
        else:
            print_error(f"Error retrieving holds: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@hold.command(name="list-for-title")
@click.argument("biblio_id", type=int, required=True)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def list_for_title(biblio_id: int, api_url: str):
    """
    List all holds for a bibliographic record.

    Args:
        biblio_id: Bibliographic record ID
    """
    try:
        client = get_client(base_url=api_url)

        # Get bibliographic record
        biblio_response = client.get(f"/api/v1/catalog/bibliographic/{biblio_id}")
        if biblio_response.status_code != 200:
            print_error(f"Bibliographic record not found: {biblio_id}")
            raise click.Abort()

        biblio_data = biblio_response.json()

        # Get holds
        response = client.get(f"/api/v1/holds/bibliographic/{biblio_id}")

        if response.status_code == 200:
            holds = response.json()

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold cyan]📌 Réservations / Holds for:[/bold cyan]\n"
                    f"{biblio_data.get('title', 'N/A')}",
                    style="cyan"
                )
            )
            console.print()

            if not holds:
                console.print("[dim]Aucune réservation / No holds[/dim]")
                return

            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Pos.", justify="center", style="yellow")
            table.add_column("Emprunteur\nBorrower", style="cyan")
            table.add_column("Classe\nClass")
            table.add_column("Date réservation\nHold date")
            table.add_column("Statut\nStatus")

            for hold in holds:
                status_display = {
                    "waiting": "🟡 En attente",
                    "ready": "🟢 Prêt",
                    "fulfilled": "✅ Retiré",
                    "cancelled": "❌ Annulé",
                    "expired": "⏱️ Expiré",
                }.get(hold.get("status", ""), hold.get("status", ""))

                table.add_row(
                    str(hold.get("queue_position", "-")),
                    hold.get("borrower_name", "N/A"),
                    hold.get("borrower_class", "N/A") or "-",
                    hold.get("hold_date", "N/A")[:10],
                    status_display,
                )

            console.print(table)
        else:
            print_error(f"Error retrieving holds: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@hold.command(name="cancel")
@click.argument("hold_id", type=int, required=True)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def cancel_hold(hold_id: int, api_url: str):
    """
    Cancel a hold.

    Args:
        hold_id: Hold ID
    """
    try:
        client = get_client(base_url=api_url)

        # Get hold details first
        hold_response = client.get(f"/api/v1/holds/{hold_id}")
        if hold_response.status_code != 200:
            print_error(f"Hold not found: {hold_id}")
            raise click.Abort()

        hold_data = hold_response.json()

        # Confirm
        console.print()
        console.print(f"[bold]Hold ID:[/bold] {hold_id}")
        console.print(f"[bold]Borrower:[/bold] {hold_data.get('borrower_name', 'N/A')}")
        console.print(f"[bold]Title:[/bold] {hold_data.get('title', 'N/A')}")
        console.print(f"[bold]Status:[/bold] {hold_data.get('status', 'N/A')}")
        console.print()

        if not click.confirm("Annuler cette réservation ? / Cancel this hold?", default=False):
            console.print("[yellow]Opération annulée / Operation cancelled[/yellow]")
            return

        # Cancel hold
        response = client.delete(f"/api/v1/holds/{hold_id}")

        if response.status_code == 204:
            console.print("[green]✅ Réservation annulée / Hold cancelled[/green]")
        else:
            error_data = response.json() if response.headers.get("content-type", "").startswith(
                "application/json"
            ) else {}
            print_error(f"Error cancelling hold: {error_data.get('detail', response.text)}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@hold.command(name="ready")
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def ready_holds(api_url: str):
    """Show holds ready for pickup."""
    try:
        client = get_client(base_url=api_url)

        response = client.get("/api/v1/holds/ready")

        if response.status_code == 200:
            holds = response.json()

            # Header
            console.print()
            console.print(
                Panel(
                    "[bold cyan]📦 Réservations prêtes / Holds Ready for Pickup[/bold cyan]",
                    style="cyan"
                )
            )
            console.print()

            if not holds:
                console.print("[dim]Aucune réservation prête / No holds ready[/dim]")
                return

            # Create table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Emprunteur\nBorrower", style="cyan")
            table.add_column("Classe\nClass")
            table.add_column("Titre\nTitle", style="green")
            table.add_column("Expire dans\nExpires in", justify="center")

            for hold in holds:
                # Calculate days until expiration
                from datetime import date, datetime
                exp_date = hold.get("expiration_date")
                if exp_date:
                    try:
                        exp = datetime.strptime(exp_date, "%Y-%m-%d").date()
                        days_left = (exp - date.today()).days
                        if days_left < 0:
                            expires_display = "[red]Expiré[/red]"
                        elif days_left == 0:
                            expires_display = "[yellow]Aujourd'hui[/yellow]"
                        elif days_left == 1:
                            expires_display = "[yellow]1 jour[/yellow]"
                        else:
                            expires_display = f"{days_left} jours"
                    except (ValueError, TypeError):
                        expires_display = exp_date
                else:
                    expires_display = "-"

                table.add_row(
                    hold.get("borrower_name", "N/A"),
                    hold.get("borrower_class", "N/A") or "-",
                    hold.get("title", "N/A")[:40],
                    expires_display,
                )

            console.print(table)
            console.print()
            console.print(
                "[dim]💡 Tip: Notifiez les emprunteurs / Notify borrowers[/dim]"
            )
        else:
            print_error(f"Error retrieving ready holds: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()
