"""
Checkout command

Interactive and direct checkout workflows.
"""

from typing import List, Optional

import click

from ..client import get_client
from ..utils.display import (
    confirm,
    console,
    print_borrower_info,
    print_checkout_summary,
    print_error,
    print_header,
    print_warning,
)
from ..utils.scanner import read_barcode_input


@click.command(name="checkout")
@click.argument("borrower_id", required=False)
@click.argument("item_ids", nargs=-1, required=False)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def checkout(
    borrower_id: Optional[str],
    item_ids: tuple,
    api_url: str,
):
    """
    Checkout items to a borrower.

    \b
    Interactive mode (barcode scanner):
        bcd-cli checkout

    \b
    Direct mode:
        bcd-cli checkout <borrower-id> <item-id1> <item-id2> ...
        bcd-cli checkout 101 785 787
    """
    try:
        client = get_client(base_url=api_url)

        # Determine mode
        if borrower_id is None:
            # Interactive mode
            _checkout_interactive(client)
        else:
            # Direct mode
            if not item_ids:
                print_error("Au moins un item ID requis / At least one item ID required")
                print_warning(
                    "Usage: bcd-cli checkout <borrower-id> <item-id1> [<item-id2> ...]"
                )
                raise click.Abort()

            _checkout_direct(client, borrower_id, list(item_ids))

    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée / Operation cancelled[/yellow]")
        raise click.Abort()
    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


def _checkout_interactive(client):
    """
    Interactive checkout workflow with barcode scanner.

    Args:
        client: API client instance
    """
    print_header("📖 BCD Library - Prêt / Checkout")

    # Step 1: Scan borrower ID
    console.print("[bold cyan]Scannez l'ID de l'emprunteur / Scan borrower ID[/bold cyan]")
    borrower_id = read_barcode_input("> ")

    if not borrower_id:
        print_warning("ID emprunteur vide / Empty borrower ID")
        return

    # Step 2: Get borrower info
    try:
        borrower_data = client.get_borrower_current_loans(borrower_id)
        print_borrower_info(borrower_data)

        # Check if borrower is blocked
        if not borrower_data.get("active", True):
            print_error(
                f"Emprunteur bloqué / Borrower blocked: {borrower_data.get('blocked_reason', 'Unknown')}"
            )
            return

    except Exception as e:
        print_error(f"Emprunteur non trouvé / Borrower not found: {borrower_id}")
        print_warning(f"Détails / Details: {str(e)}")
        return

    # Step 3: Scan items
    console.print()
    console.print(
        "[bold cyan]Scannez le code-barres du document (Entrée pour terminer)[/bold cyan]"
    )
    console.print("[bold cyan]Scan item barcode (Enter to finish)[/bold cyan]")

    item_ids = []
    while True:
        item_id = read_barcode_input("> ")

        if not item_id:
            # Empty = done
            break

        # Validate item exists (optional - API will validate)
        item_ids.append(item_id)
        console.print(f"  [green]✓[/green] Ajouté / Added: Item {item_id}")

    if not item_ids:
        print_warning("Aucun document scanné / No items scanned")
        return

    # Step 4: Confirm and checkout
    console.print()
    console.print(f"[bold]Total documents / Total items: {len(item_ids)}[/bold]")
    console.print()

    if not confirm("Confirmer le prêt ? / Confirm checkout?", default=True):
        print_warning("Prêt annulé / Checkout cancelled")
        return

    # Step 5: Call API
    try:
        result = client.checkout(
            borrower_id=borrower_id, item_ids=item_ids, checked_out_by="cli"
        )
        print_checkout_summary(result)

    except Exception as e:
        print_error(f"Échec du prêt / Checkout failed: {str(e)}")
        raise


def _checkout_direct(client, borrower_id: str, item_ids: List[str]):
    """
    Direct checkout mode (command-line arguments).

    Args:
        client: API client instance
        borrower_id: Borrower ID
        item_ids: List of item IDs
    """
    print_header("📖 BCD Library - Prêt / Checkout")

    console.print(f"Emprunteur / Borrower: {borrower_id}")
    console.print(f"Documents / Items: {', '.join(item_ids)}")
    console.print()

    try:
        result = client.checkout(
            borrower_id=borrower_id, item_ids=item_ids, checked_out_by="cli"
        )
        print_checkout_summary(result)

    except Exception as e:
        print_error(f"Échec du prêt / Checkout failed: {str(e)}")
        raise
