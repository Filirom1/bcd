"""
Report commands

Commands for generating library reports and statistics.
"""

import click
from typing import Optional
from ..client import get_client
from ..utils.display import console, print_error
from rich.table import Table
from rich.panel import Panel


@click.group(name="report")
def report():
    """Generate library reports and statistics."""
    pass


@report.command(name="overdue")
@click.option(
    "--class",
    "class_name",
    help="Filter by class name (e.g., CP-A)",
)
@click.option(
    "--academic-year",
    help="Filter by academic year (e.g., 2025-2026)",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def overdue_report(class_name: Optional[str], academic_year: Optional[str], api_url: str):
    """
    Generate overdue items report.

    Shows all items currently overdue with borrower information.
    """
    try:
        client = get_client(base_url=api_url)

        # Build query params
        params = {}
        if class_name:
            params["class_name"] = class_name
        if academic_year:
            params["academic_year"] = academic_year

        response = client.get("/api/v1/reports/overdue", params=params)

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            total = data.get("total_overdue", 0)

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold red]📊 Rapport des retards / Overdue Report[/bold red]\n"
                    f"Total: {total} document(s) en retard / overdue",
                    style="red"
                )
            )
            console.print()

            if not items:
                console.print("[green]✅ Aucun document en retard / No overdue items[/green]")
                return

            # Group by class if not filtered
            if not class_name:
                # Show summary by class first
                summary_response = client.get(
                    "/api/v1/reports/overdue/by-class", params=params
                )
                if summary_response.status_code == 200:
                    summary_data = summary_response.json()
                    classes = summary_data.get("classes", [])

                    if classes:
                        console.print("[bold]Résumé par classe / Summary by Class:[/bold]")
                        console.print()

                        summary_table = Table(show_header=True, header_style="bold")
                        summary_table.add_column("Classe / Class", style="cyan")
                        summary_table.add_column("Retards / Overdue", justify="center", style="red")

                        for class_info in classes:
                            summary_table.add_row(
                                class_info["class_name"],
                                str(class_info["overdue_count"]),
                            )

                        console.print(summary_table)
                        console.print()

            # Detailed table
            console.print("[bold]Détails / Details:[/bold]")
            console.print()

            table = Table(show_header=True, header_style="bold")
            table.add_column("Emprunteur\nBorrower", style="cyan")
            table.add_column("Classe\nClass")
            table.add_column("Document\nItem ID", style="yellow")
            table.add_column("Titre / Title", style="green", max_width=30)
            table.add_column("Dû le\nDue", style="yellow")
            table.add_column("Retard\nDays", justify="center", style="red")

            for item in items:
                table.add_row(
                    item.get("borrower_name", "N/A"),
                    item.get("class_name", "-") or "-",
                    item.get("item_id", "N/A"),
                    item.get("title", "N/A")[:30],
                    str(item.get("due_date", "N/A")),
                    f"+{item.get('days_overdue', 0)}j",
                )

            console.print(table)

        else:
            print_error(f"Error retrieving report: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@report.command(name="never-borrowed")
@click.option(
    "--academic-year",
    help="Filter by acquisition year (e.g., 2025-2026)",
)
@click.option(
    "--limit",
    default=50,
    type=int,
    help="Maximum number of results to display",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def never_borrowed_report(academic_year: Optional[str], limit: int, api_url: str):
    """
    Generate never-borrowed items report.

    Shows items that have never been checked out.
    """
    try:
        client = get_client(base_url=api_url)

        # Build query params
        params = {"limit": limit}
        if academic_year:
            params["academic_year"] = academic_year

        response = client.get("/api/v1/reports/never-borrowed", params=params)

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            total = data.get("total_count", 0)

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold yellow]📊 Documents jamais empruntés / Never Borrowed Report[/bold yellow]\n"
                    f"Total: {total} document(s)",
                    style="yellow"
                )
            )
            console.print()

            if not items:
                console.print("[green]✅ Tous les documents ont été empruntés / All items have been borrowed[/green]")
                return

            # Table
            table = Table(show_header=True, header_style="bold")
            table.add_column("ID", style="dim")
            table.add_column("Titre / Title", style="cyan", max_width=35)
            table.add_column("Auteur / Author", max_width=20)
            table.add_column("Année\nYear", justify="center")
            table.add_column("Cote\nCall #")

            for item in items:
                table.add_row(
                    item.get("item_id", "N/A"),
                    item.get("title", "N/A")[:35],
                    (item.get("authors") or "N/A")[:20],
                    str(item.get("publication_year") or "-"),
                    item.get("call_number") or "-",
                )

            console.print(table)

            console.print()
            console.print(
                f"[dim]💡 Affichage de {min(limit, total)} sur {total} résultats / "
                f"Showing {min(limit, total)} of {total} results[/dim]"
            )

        else:
            print_error(f"Error retrieving report: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@report.command(name="most-borrowed")
@click.option(
    "--period",
    type=click.Choice(["month", "year", "all-time"]),
    default="year",
    help="Time period for report",
)
@click.option(
    "--limit",
    default=20,
    type=int,
    help="Number of top titles to display",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def most_borrowed_report(period: str, limit: int, api_url: str):
    """
    Generate most borrowed titles report.

    Shows the most popular titles by circulation count.
    """
    try:
        client = get_client(base_url=api_url)

        params = {"period": period, "limit": limit}
        response = client.get("/api/v1/reports/most-borrowed", params=params)

        if response.status_code == 200:
            data = response.json()
            titles = data.get("titles", [])

            # Period label
            period_labels = {
                "month": "Dernier mois / Last Month",
                "year": "Dernière année / Last Year",
                "all-time": "Depuis toujours / All Time",
            }
            period_label = period_labels.get(period, period)

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold green]📊 Titres les plus empruntés / Most Borrowed Titles[/bold green]\n"
                    f"Période / Period: {period_label}",
                    style="green"
                )
            )
            console.print()

            if not titles:
                console.print("[yellow]Aucune donnée disponible / No data available[/yellow]")
                return

            # Table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Rang\nRank", justify="center", style="yellow")
            table.add_column("Titre / Title", style="cyan", max_width=35)
            table.add_column("Auteur / Author", max_width=20)
            table.add_column("Année\nYear", justify="center")
            table.add_column("Prêts\nCheckouts", justify="center", style="green")

            for title in titles:
                table.add_row(
                    str(title.get("rank", "-")),
                    title.get("title", "N/A")[:35],
                    (title.get("authors") or "N/A")[:20],
                    str(title.get("publication_year") or "-"),
                    str(title.get("checkout_count", 0)),
                )

            console.print(table)

        else:
            print_error(f"Error retrieving report: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@report.command(name="statistics")
@click.option(
    "--period",
    type=click.Choice(["month", "year", "all-time"]),
    default="year",
    help="Time period for statistics",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def statistics_report(period: str, api_url: str):
    """
    Display circulation statistics.

    Shows overall library usage statistics.
    """
    try:
        client = get_client(base_url=api_url)

        params = {"period": period}
        response = client.get("/api/v1/reports/statistics", params=params)

        if response.status_code == 200:
            stats = response.json()

            # Header
            console.print()
            console.print(
                Panel(
                    f"[bold cyan]📊 Statistiques de circulation / Circulation Statistics[/bold cyan]\n"
                    f"Période / Period: {stats.get('period', period)}",
                    style="cyan"
                )
            )
            console.print()

            # Display statistics
            console.print("[bold]Circulation générale / General Circulation:[/bold]")
            console.print(
                f"  Total prêts / Total checkouts: [green]{stats.get('total_checkouts', 0)}[/green]"
            )
            console.print(
                f"  Documents en prêt / Items on loan: [yellow]{stats.get('items_on_loan', 0)}[/yellow]"
            )
            console.print(
                f"  Documents en retard / Overdue items: [red]{stats.get('overdue_items', 0)}[/red]"
            )
            console.print(
                f"  Emprunteurs actifs / Active borrowers: [cyan]{stats.get('active_borrowers', 0)}[/cyan]"
            )

            if stats.get("average_loans_per_day"):
                console.print(
                    f"  Moyenne par jour / Avg per day: {stats['average_loans_per_day']}"
                )

            console.print()

            console.print("[bold]Renouvellements et retours / Renewals & Returns:[/bold]")
            console.print(
                f"  Renouvellements / Renewals: {stats.get('renewals', 0)}"
            )
            console.print(
                f"  Documents retournés / Returned items: {stats.get('returned_items', 0)}"
            )
            console.print(
                f"  Retours en retard / Late returns: {stats.get('late_returns', 0)}"
            )
            console.print(
                f"  Taux de retard / Late return rate: {stats.get('late_return_rate', 0)}%"
            )

        else:
            print_error(f"Error retrieving statistics: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()
