"""
Display utilities using Rich library

Provides formatted console output with tables, colors, and progress indicators.
"""

from datetime import date, datetime
from typing import Any, Dict

from rich.console import Console
from rich.table import Table

# Console instance
console = Console()


def print_header(title: str):
    """Print section header."""
    console.print()
    console.print(f"[bold blue]{title}[/bold blue]")
    console.print("━" * 60)
    console.print()


def print_success(message: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {message}", style="bold red")


def print_warning(message: str):
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_info(message: str):
    """Print info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


def format_date(d: Any) -> str:
    """
    Format date for display.

    Args:
        d: Date object, string, or None

    Returns:
        Formatted date string
    """
    if d is None:
        return "N/A"
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d.replace("Z", "+00:00"))
        except:
            return d
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def print_borrower_info(borrower_data: Dict[str, Any]):
    """
    Display borrower information.

    Args:
        borrower_data: Borrower data from API
    """
    console.print()
    console.print(
        f"[green]✓[/green] Emprunteur / Borrower: [bold]{borrower_data.get('full_name', 'N/A')}[/bold]"
    )

    if borrower_data.get("class_name"):
        console.print(f"  Classe / Class: {borrower_data['class_name']}")

    # Current loans
    current = borrower_data.get("current_loans_count", 0)
    limit = borrower_data.get("loan_limit", 2)
    console.print(f"  Prêts en cours / Current loans: {current}/{limit}")

    # Status
    is_active = borrower_data.get("active", True)
    if is_active:
        console.print("  Statut / Status: [green]Actif / Active[/green]")
    else:
        reason = borrower_data.get("blocked_reason", "Unknown")
        console.print(
            f"  Statut / Status: [red]Bloqué / Blocked[/red] - {reason}",
            style="bold red",
        )


def print_item_added(item_data: Dict[str, Any]):
    """
    Display item added confirmation.

    Args:
        item_data: Item data from API
    """
    console.print()
    console.print(
        f"[green]✓[/green] Ajouté / Added: [bold]{item_data.get('title', 'N/A')}[/bold]"
    )

    if item_data.get("authors"):
        authors = item_data["authors"]
        if isinstance(authors, list):
            authors = ", ".join(authors)
        console.print(f"  Auteur / Author: {authors}")

    if item_data.get("call_number"):
        console.print(f"  Cote / Call #: {item_data['call_number']}")


def print_checkout_summary(checkout_data: Dict[str, Any]):
    """
    Display checkout summary table.

    Args:
        checkout_data: Checkout response from API
    """
    console.print()
    console.print("[bold]Résumé du prêt / Checkout Summary:[/bold]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Item ID", style="white")
    table.add_column("Titre / Title", style="white", max_width=40)
    table.add_column("Date retour\nDue Date", style="white")

    for transaction in checkout_data.get("transactions", []):
        table.add_row(
            transaction.get("item_id", "N/A"),
            transaction.get("title", "N/A"),
            format_date(transaction.get("due_date")),
        )

    console.print(table)
    console.print()

    # Summary message
    count = checkout_data.get("items_checked_out", 0)
    borrower = checkout_data.get("borrower_name", "N/A")
    console.print(
        f"[green]✅ {count} document(s) prêté(s) à {borrower}[/green]",
        style="bold green",
    )
    console.print(f"   {count} item(s) checked out to {borrower}", style="green")


def print_return_summary(return_data: Dict[str, Any]):
    """
    Display return summary table.

    Args:
        return_data: Return response from API
    """
    console.print()
    console.print("[bold]Résumé du retour / Return Summary:[/bold]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Item ID", style="white")
    table.add_column("Titre / Title", style="white", max_width=30)
    table.add_column("Emprunteur\nBorrower", style="white", max_width=20)
    table.add_column("Statut\nStatus", style="white")

    for item in return_data.get("items", []):
        # Status indicator
        was_overdue = item.get("was_overdue", False)
        days_overdue = item.get("days_overdue", 0)

        if was_overdue:
            status = f"[yellow]⚠ +{days_overdue}j[/yellow]"
        else:
            status = "[green]✓[/green]"

        table.add_row(
            item.get("item_id", "N/A"),
            item.get("title", "N/A"),
            item.get("borrower_name", "N/A"),
            status,
        )

    console.print(table)
    console.print()

    # Summary messages
    count = return_data.get("items_returned", 0)
    overdue_count = return_data.get("overdue_count", 0)

    console.print(
        f"[green]✅ {count} document(s) retourné(s)[/green]", style="bold green"
    )
    console.print(f"   {count} item(s) returned", style="green")

    if overdue_count > 0:
        console.print()
        console.print(
            f"[yellow]⚠ {overdue_count} document(s) en retard / overdue item(s)[/yellow]",
            style="bold yellow",
        )

        # Check if borrower was blocked
        if return_data.get("borrower_blocked"):
            console.print(
                "   [red]→ L'emprunteur a été bloqué / Borrower has been blocked[/red]"
            )


def print_renewal_summary(renewal_data: Dict[str, Any]):
    """
    Display renewal summary.

    Args:
        renewal_data: Renewal response from API
    """
    console.print()

    renewed = renewal_data.get("items_renewed", [])
    failed = renewal_data.get("items_not_renewed", [])

    if renewed:
        console.print(
            f"[green]✅ {len(renewed)} document(s) renouvelé(s)[/green]",
            style="bold green",
        )
        console.print(f"   {len(renewed)} item(s) renewed", style="green")
        console.print()

        for item in renewed:
            console.print(
                f"  [green]✓[/green] Item {item.get('item_id')}: "
                f"Nouvelle date / New due date: {format_date(item.get('new_due_date'))}"
            )

    if failed:
        console.print()
        console.print(
            f"[yellow]⚠ {len(failed)} document(s) non renouvelé(s)[/yellow]",
            style="bold yellow",
        )
        console.print(f"   {len(failed)} item(s) not renewed", style="yellow")
        console.print()

        for item in failed:
            reason = item.get("reason", "Unknown")
            console.print(f"  [yellow]✗[/yellow] Item {item.get('item_id')}: {reason}")


def print_current_loans_table(loans_data: Dict[str, Any]):
    """
    Display current loans in a table.

    Args:
        loans_data: Current loans data from API
    """
    loans = loans_data.get("current_loans", [])

    if not loans:
        console.print("[dim]Aucun prêt en cours / No current loans[/dim]")
        return

    console.print()
    console.print(f"[bold]Prêts en cours / Current Loans: {len(loans)}[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Item ID", style="white")
    table.add_column("Titre / Title", style="white", max_width=30)
    table.add_column("Dû le\nDue", style="white")
    table.add_column("Renouv.\nRenewals", style="white")
    table.add_column("Peut renouveler?\nCan Renew?", style="white")

    for idx, loan in enumerate(loans, start=1):
        # Check if can renew
        can_renew = loan.get("can_renew", False)
        renew_str = "[green]✓ Oui[/green]" if can_renew else "[red]✗ Non[/red]"

        # Check if overdue
        is_overdue = loan.get("is_overdue", False)
        due_date_str = format_date(loan.get("due_date"))
        if is_overdue:
            due_date_str = f"[red]{due_date_str}[/red]"

        # Renewal count
        renewal_count = loan.get("renewal_count", 0)
        renewal_limit = loan.get("renewal_limit", 2)
        renewal_str = f"{renewal_count}/{renewal_limit}"

        table.add_row(
            str(idx),
            loan.get("item_id", "N/A"),
            loan.get("title", "N/A"),
            due_date_str,
            renewal_str,
            renew_str,
        )

    console.print(table)


def confirm(prompt: str, default: bool = True) -> bool:
    """
    Ask for user confirmation.

    Args:
        prompt: Confirmation prompt
        default: Default value

    Returns:
        True if confirmed, False otherwise
    """
    default_str = "O/n" if default else "o/N"
    user_input = console.input(f"{prompt} [{default_str}]: ").strip().lower()

    if not user_input:
        return default

    return user_input in ["o", "oui", "y", "yes"]
