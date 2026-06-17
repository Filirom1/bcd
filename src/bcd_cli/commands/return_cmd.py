"""
Return command

Interactive and direct return workflows.
"""

import click
from typing import List, Optional
from ..client import get_client
from ..utils.display import (
    console,
    print_header,
    print_return_summary,
    print_error,
    print_warning,
    confirm,
    format_date,
)
from ..utils.scanner import read_barcode_input


@click.command(name="return")
@click.argument("item_ids", nargs=-1, required=False)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def return_items(
    item_ids: tuple,
    api_url: str,
):
    """
    Return items.

    \b
    Interactive mode (barcode scanner):
        bcd return

    \b
    Direct mode:
        bcd return <item-id1> <item-id2> ...
        bcd return 785 787
    """
    try:
        client = get_client(base_url=api_url)

        # Determine mode
        if not item_ids:
            # Interactive mode
            _return_interactive(client)
        else:
            # Direct mode
            _return_direct(client, list(item_ids))

    except KeyboardInterrupt:
        console.print("\n[yellow]Opération annulée / Operation cancelled[/yellow]")
        raise click.Abort()
    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


def _return_interactive(client):
    """
    Interactive return workflow with barcode scanner.

    Args:
        client: API client instance
    """
    print_header("📖 BCD Library - Retour / Return")

    console.print(
        "[bold cyan]Scannez le code-barres du document (Entrée pour terminer)[/bold cyan]"
    )
    console.print("[bold cyan]Scan item barcode (Enter to finish)[/bold cyan]")
    console.print()

    item_ids = []
    item_details = []

    while True:
        item_id = read_barcode_input("> ")

        if not item_id:
            # Empty = done
            break

        # Get item info to show borrower and status
        try:
            item_info = client.get_item_history(item_id)
            current_loan = item_info.get("current_loan")

            if current_loan:
                # Show item details
                console.print(
                    f"  [green]✓[/green] Document / Item: [bold]{item_info.get('title', 'N/A')}[/bold] (ID: {item_id})"
                )
                console.print(
                    f"    Emprunteur / Borrower: {current_loan.get('borrower_name', 'N/A')}"
                )
                console.print(
                    f"    Prêté le / Checked out: {format_date(current_loan.get('checkout_date'))}"
                )
                console.print(
                    f"    Dû le / Due: {format_date(current_loan.get('due_date'))}"
                )

                # Check if overdue
                is_overdue = current_loan.get("is_overdue", False)
                days_overdue = current_loan.get("days_overdue", 0)

                if is_overdue:
                    console.print(
                        f"    [red]⚠ En retard de {days_overdue} jour(s) / {days_overdue} day(s) overdue[/red]"
                    )
                else:
                    console.print("    [green]✓ À temps / On time[/green]")

                item_ids.append(item_id)
                item_details.append(item_info)
            else:
                console.print(
                    f"  [yellow]⚠[/yellow] Document {item_id}: Pas en prêt / Not on loan"
                )

        except Exception as e:
            console.print(
                f"  [red]✗[/red] Document {item_id}: Non trouvé / Not found"
            )
            console.print(f"    [dim]{str(e)}[/dim]")

        console.print()

    if not item_ids:
        print_warning("Aucun document scanné / No items scanned")
        return

    # Confirm return
    console.print(f"[bold]Total documents / Total items: {len(item_ids)}[/bold]")
    console.print()

    if not confirm("Confirmer le retour ? / Confirm return?", default=True):
        print_warning("Retour annulé / Return cancelled")
        return

    # Call API
    try:
        result = client.return_items(item_ids=item_ids, returned_by="cli")
        print_return_summary(result)

    except Exception as e:
        print_error(f"Échec du retour / Return failed: {str(e)}")
        raise


def _return_direct(client, item_ids: List[str]):
    """
    Direct return mode (command-line arguments).

    Args:
        client: API client instance
        item_ids: List of item IDs
    """
    print_header("📖 BCD Library - Retour / Return")

    console.print(f"Documents / Items: {', '.join(item_ids)}")
    console.print()

    try:
        result = client.return_items(item_ids=item_ids, returned_by="cli")
        print_return_summary(result)

    except Exception as e:
        print_error(f"Échec du retour / Return failed: {str(e)}")
        raise
