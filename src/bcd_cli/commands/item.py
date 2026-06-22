"""
Item commands

Commands for viewing item status and circulation history.
"""


import click
from rich.panel import Panel
from rich.table import Table

from ..client import get_client
from ..utils.display import console, print_error


@click.group(name="item")
def item():
    """View item status and circulation history."""
    pass


@item.command(name="status")
@click.argument("item_id", required=True)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def status(item_id: str, api_url: str):
    """
    View item status and details.

    Args:
        item_id: Item ID (inventory number)
    """
    try:
        client = get_client(base_url=api_url)

        # Get item details
        response = client.get(f"/api/v1/catalog/items/{item_id}")

        if response.status_code == 200:
            item_data = response.json()

            # Display item header
            console.print(
                Panel(
                    f"[bold cyan]Exemplaire / Item: {item_id}[/bold cyan]",
                    style="cyan"
                )
            )
            console.print()

            # Bibliographic info
            console.print(f"[bold]Titre / Title:[/bold] {item_data.get('title', 'N/A')}")
            if item_data.get('authors'):
                console.print(f"[bold]Auteur / Author:[/bold] {item_data['authors']}")
            console.print(f"[bold]Cote / Call #:[/bold] {item_data.get('call_number', 'N/A')}")

            if item_data.get('shelf_location'):
                console.print(
                    f"[bold]Emplacement / Location:[/bold] {item_data['shelf_location']}"
                )
            console.print()

            # Status
            status_color = {
                "available": "green",
                "on_loan": "red",
                "on_hold": "yellow",
                "in_repair": "yellow",
                "lost": "red",
                "withdrawn": "dim",
            }.get(item_data.get("status", ""), "white")

            status_text = {
                "available": "🟢 Disponible / Available",
                "on_loan": "🔴 En prêt / On loan",
                "on_hold": "🟡 Réservé / On hold",
                "in_repair": "🟡 En réparation / In repair",
                "lost": "🔴 Perdu / Lost",
                "withdrawn": "⚫ Retiré / Withdrawn",
            }.get(item_data.get("status", ""), item_data.get("status", "Unknown"))

            console.print(f"[bold]Statut / Status:[/bold] [{status_color}]{status_text}[/{status_color}]")

            # If on loan, show borrower info
            if item_data.get("status") == "on_loan" and item_data.get("current_borrower"):
                borrower = item_data["current_borrower"]
                console.print(
                    f"  [bold]Emprunteur / Borrower:[/bold] {borrower.get('full_name', 'N/A')} "
                    f"({borrower.get('class_name', 'N/A')})"
                )
                if borrower.get("checkout_date"):
                    console.print(
                        f"  [bold]Prêté le / Checked out:[/bold] {borrower['checkout_date']}"
                    )
                if borrower.get("due_date"):
                    console.print(f"  [bold]Dû le / Due:[/bold] {borrower['due_date']}")

            console.print()

            # Condition and loanability
            condition_emoji = {
                "good": "✅",
                "damaged": "⚠️",
                "lost": "❌",
                "withdrawn": "🗑️",
            }.get(item_data.get("condition", ""), "")

            console.print(
                f"[bold]État / Condition:[/bold] {condition_emoji} "
                f"{item_data.get('condition', 'N/A').title()}"
            )
            console.print(
                f"[bold]Empruntable / Loanable:[/bold] "
                f"{'Oui / Yes' if item_data.get('loanable') else 'Non / No'}"
            )

            # Additional info
            if item_data.get("acquisition_date"):
                console.print(
                    f"[bold]Date d'achat / Acquisition date:[/bold] {item_data['acquisition_date']}"
                )
            if item_data.get("funding_source"):
                console.print(
                    f"[bold]Financement / Funding:[/bold] {item_data['funding_source']}"
                )


        elif response.status_code == 404:
            print_error(f"Item not found / Document non trouvé: {item_id}")
        else:
            print_error(f"Error retrieving item: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@item.command(name="history")
@click.argument("item_id", required=True)
@click.option(
    "--limit",
    default=10,
    type=int,
    help="Maximum number of records to display",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def history(item_id: str, limit: int, api_url: str):
    """
    View item circulation history.

    Args:
        item_id: Item ID (inventory number)
        limit: Maximum number of records to display
    """
    try:
        client = get_client(base_url=api_url)

        # Get circulation history
        response = client.get(f"/api/v1/circulation/item/{item_id}/history")

        if response.status_code == 200:
            data = response.json()

            # Header
            console.print(
                Panel(
                    f"[bold cyan]Historique de circulation / Circulation History[/bold cyan]\n"
                    f"Item {item_id}: {data.get('title', 'N/A')}",
                    style="cyan"
                )
            )
            console.print()

            # Current loan
            if data.get("current_loan"):
                loan = data["current_loan"]
                console.print("[bold red]🔴 Prêt en cours / Current Loan:[/bold red]")
                console.print(
                    f"   Emprunteur / Borrower: {loan.get('borrower_full_name', 'N/A')} "
                    f"({loan.get('class_name', 'N/A')})"
                )
                console.print(
                    f"   Depuis / Since: {loan.get('checkout_date', 'N/A')}"
                )
                console.print(
                    f"   Retour prévu / Due: {loan.get('due_date', 'N/A')}"
                )
                console.print()

            # History
            history_list = data.get("history", [])[:limit]
            if history_list:
                console.print(
                    f"[bold]📜 Historique / History "
                    f"({len(history_list)} derniers prêts / last loans):[/bold]"
                )
                console.print()

                table = Table(show_header=True, header_style="bold")
                table.add_column("Emprunteur\nBorrower", style="cyan")
                table.add_column("Prêt\nCheckout", style="green")
                table.add_column("Retour\nReturn", style="green")
                table.add_column("Retard\nLate", style="yellow")

                for h in history_list:
                    borrower_name = h.get("borrower_full_name", "N/A")
                    class_name = h.get("class_name")
                    if class_name:
                        borrower_display = f"{borrower_name[:15]}... ({class_name})" if len(
                            borrower_name
                        ) > 15 else f"{borrower_name} ({class_name})"
                    else:
                        borrower_display = borrower_name

                    checkout = h.get("checkout_date", "N/A")
                    return_date = h.get("return_date", "(en cours)")

                    # Calculate days late
                    late = ""
                    if h.get("days_overdue", 0) > 0:
                        late = f"+{h['days_overdue']}j"

                    table.add_row(
                        borrower_display,
                        checkout,
                        return_date,
                        late,
                    )

                console.print(table)
                console.print()

                # Statistics
                stats = data.get("statistics", {})
                if stats:
                    console.print("[bold]📊 Statistiques / Statistics:[/bold]")
                    if stats.get("late_return_rate"):
                        console.print(
                            f"   Taux de retard / Late rate: {stats['late_return_rate']:.1f}%"
                        )

            else:
                console.print("[dim]Aucun historique / No history available[/dim]")

        elif response.status_code == 404:
            print_error(f"Item not found / Document non trouvé: {item_id}")
        else:
            print_error(f"Error retrieving history: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()
