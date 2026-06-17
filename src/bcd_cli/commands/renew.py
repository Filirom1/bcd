"""
Renew command

Interactive renewal workflow.
"""

import click
from typing import List, Optional
from ..client import get_client
from ..utils.display import (
    console,
    print_header,
    print_borrower_info,
    print_renewal_summary,
    print_current_loans_table,
    print_error,
    print_warning,
    confirm,
)
from ..utils.scanner import read_barcode_input, read_selection_from_list


@click.command(name="renew")
@click.argument("borrower_id", required=False)
@click.option("--all", "renew_all", is_flag=True, help="Renew all eligible items")
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def renew(
    borrower_id: Optional[str],
    renew_all: bool,
    api_url: str,
):
    """
    Renew items for a borrower.

    \b
    Interactive mode (select items):
        bcd renew <borrower-id>
        bcd renew 101

    \b
    Renew all eligible items:
        bcd renew <borrower-id> --all
        bcd renew 101 --all
    """
    try:
        client = get_client(base_url=api_url)

        # Borrower ID is required
        if borrower_id is None:
            console.print(
                "[bold cyan]Scannez l'ID de l'emprunteur / Scan borrower ID[/bold cyan]"
            )
            borrower_id = read_barcode_input("> ")

            if not borrower_id:
                print_warning("ID emprunteur vide / Empty borrower ID")
                return

        if renew_all:
            # Renew all eligible items
            _renew_all(client, borrower_id)
        else:
            # Interactive selection
            _renew_interactive(client, borrower_id)

    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée / Operation cancelled[/yellow]")
        raise click.Abort()
    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


def _renew_interactive(client, borrower_id: str):
    """
    Interactive renewal with item selection.

    Args:
        client: API client instance
        borrower_id: Borrower ID
    """
    print_header("📖 BCD Library - Renouvellement / Renewal")

    # Get current loans
    try:
        loans_data = client.get_borrower_current_loans(borrower_id)
    except Exception as e:
        print_error(f"Emprunteur non trouvé / Borrower not found: {borrower_id}")
        print_warning(f"Détails / Details: {str(e)}")
        return

    # Show borrower info
    print_borrower_info(loans_data)

    # Show current loans
    current_loans = loans_data.get("current_loans", [])

    if not current_loans:
        console.print()
        console.print("[dim]Aucun prêt en cours / No current loans[/dim]")
        return

    # Display loans table
    print_current_loans_table(loans_data)

    # Select items to renew
    console.print()
    console.print(
        "[bold]Sélectionner les documents à renouveler / Select items to renew[/bold]"
    )
    console.print("[dim](Entrez les numéros séparés par des virgules: 1,2,3)[/dim]")
    console.print("[dim](Enter numbers separated by commas: 1,2,3)[/dim]")

    selected_indices = read_selection_from_list(
        max_items=len(current_loans),
        prompt="Sélectionner / Select",
    )

    if not selected_indices:
        print_warning("Aucun document sélectionné / No items selected")
        return

    # Get item IDs from selection
    selected_item_ids = []
    for idx in selected_indices:
        if 1 <= idx <= len(current_loans):
            item_id = current_loans[idx - 1].get("item_id")
            if item_id:
                selected_item_ids.append(item_id)

    console.print()
    console.print(
        f"[bold]Documents sélectionnés / Selected items: {len(selected_item_ids)}[/bold]"
    )
    console.print()

    if not confirm("Confirmer le renouvellement ? / Confirm renewal?", default=True):
        print_warning("Renouvellement annulé / Renewal cancelled")
        return

    # Call API
    try:
        result = client.renew_items(borrower_id=borrower_id, item_ids=selected_item_ids)
        print_renewal_summary(result)

    except Exception as e:
        print_error(f"Échec du renouvellement / Renewal failed: {str(e)}")
        raise


def _renew_all(client, borrower_id: str):
    """
    Renew all eligible items for a borrower.

    Args:
        client: API client instance
        borrower_id: Borrower ID
    """
    print_header("📖 BCD Library - Renouvellement / Renewal")

    console.print(f"Emprunteur / Borrower: {borrower_id}")
    console.print(
        "[bold]Renouveler tous les documents éligibles / Renew all eligible items[/bold]"
    )
    console.print()

    # Call API with no item_ids = renew all eligible
    try:
        result = client.renew_items(borrower_id=borrower_id, item_ids=None)
        print_renewal_summary(result)

    except Exception as e:
        print_error(f"Échec du renouvellement / Renewal failed: {str(e)}")
        raise
