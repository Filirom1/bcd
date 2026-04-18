"""
Borrower commands

Commands for managing borrowers (students, teachers, staff).
"""

import click
from typing import Optional
from ..client import get_client
from ..utils.display import console, print_error
from rich.table import Table
from rich.panel import Panel


@click.group(name="borrower")
def borrower():
    """Manage borrowers (students, teachers, staff)."""
    pass


@borrower.command(name="add")
@click.option("--borrower-id", required=True, help="Unique borrower ID")
@click.option("--first-name", required=True, help="First name")
@click.option("--last-name", required=True, help="Last name")
@click.option(
    "--role",
    type=click.Choice(["student", "teacher", "staff"]),
    default="student",
    help="Borrower role",
)
@click.option("--class-id", type=int, help="Class ID (for students)")
@click.option("--email", help="Email address")
@click.option("--phone", help="Phone number")
@click.option("--notes", help="Additional notes")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def add_borrower(
    borrower_id: str,
    first_name: str,
    last_name: str,
    role: str,
    class_id: Optional[int],
    email: Optional[str],
    phone: Optional[str],
    notes: Optional[str],
    api_url: str,
):
    """Add a new borrower."""
    try:
        client = get_client(base_url=api_url)

        payload = {
            "borrower_id": borrower_id,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
        }

        if class_id is not None:
            payload["class_id"] = class_id
        if email:
            payload["email"] = email
        if phone:
            payload["phone"] = phone
        if notes:
            payload["notes"] = notes

        response = client.post("/api/v1/borrowers", json=payload)

        if response.status_code == 201:
            data = response.json()
            console.print(f"\n[green]✓[/green] Borrower created successfully")
            console.print(f"  ID: {data['borrower_id']}")
            console.print(f"  Name: {data['full_name']}")
            console.print(f"  Barcode: {data['barcode']}")
            console.print(f"  Role: {data['role']}")
            if data.get("class_id"):
                console.print(f"  Class ID: {data['class_id']}")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_error(f"Failed to create borrower: {error_detail}")

    except Exception as e:
        print_error(f"Error: {str(e)}")


@borrower.command(name="list")
@click.option("--role", type=click.Choice(["student", "teacher", "staff"]), help="Filter by role")
@click.option("--class-id", type=int, help="Filter by class ID")
@click.option("--active/--blocked", default=None, help="Filter by active status")
@click.option("--limit", default=100, help="Maximum results")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def list_borrowers(
    role: Optional[str],
    class_id: Optional[int],
    active: Optional[bool],
    limit: int,
    api_url: str,
):
    """List all borrowers with optional filters."""
    try:
        client = get_client(base_url=api_url)

        params = {"limit": limit}
        if role:
            params["role"] = role
        if class_id is not None:
            params["class_id"] = class_id
        if active is not None:
            params["active"] = active

        response = client.get("/api/v1/borrowers", params=params)

        if response.status_code == 200:
            borrowers = response.json()

            if not borrowers:
                console.print("\n[yellow]No borrowers found.[/yellow]")
                return

            # Create table
            table = Table(title=f"Borrowers ({len(borrowers)} found)")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Role", style="magenta")
            table.add_column("Class ID", style="blue")
            table.add_column("Status", style="green")

            for borrower in borrowers:
                status = "✓ Active" if borrower["active"] else "✗ Blocked"
                status_style = "green" if borrower["active"] else "red"

                class_id_str = str(borrower.get("class_id", "")) if borrower.get("class_id") else "-"

                table.add_row(
                    borrower["borrower_id"],
                    borrower["full_name"],
                    borrower["role"],
                    class_id_str,
                    f"[{status_style}]{status}[/{status_style}]",
                )

            console.print()
            console.print(table)
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_error(f"Failed to list borrowers: {error_detail}")

    except Exception as e:
        print_error(f"Error: {str(e)}")


@borrower.command(name="show")
@click.argument("borrower_id")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def show_borrower(borrower_id: str, api_url: str):
    """Show detailed information about a borrower."""
    try:
        client = get_client(base_url=api_url)

        response = client.get(f"/api/v1/borrowers/{borrower_id}")

        if response.status_code == 200:
            data = response.json()

            # Create info panel
            info_text = f"""[bold]Borrower Information[/bold]

ID: {data['borrower_id']}
Name: {data['full_name']}
Role: {data['role']}
Barcode: {data['barcode']}
Status: {'[green]Active[/green]' if data['active'] else '[red]Blocked[/red]'}
"""

            if data.get("class_id"):
                info_text += f"Class ID: {data['class_id']}\n"

            if data.get("email"):
                info_text += f"Email: {data['email']}\n"

            if data.get("phone"):
                info_text += f"Phone: {data['phone']}\n"

            if data.get("blocked_reason"):
                info_text += f"\n[red]Blocked Reason:[/red] {data['blocked_reason']}\n"

            info_text += f"\n[bold]Circulation Statistics[/bold]\n"
            info_text += f"Current Loans: {data.get('current_loans_count', 0)}\n"
            info_text += f"Total Checkouts: {data.get('total_checkouts', 0)}\n"
            info_text += f"Overdue Items: {data.get('overdue_count', 0)}\n"

            panel = Panel(info_text, border_style="blue")
            console.print()
            console.print(panel)

        elif response.status_code == 404:
            print_error(f"Borrower '{borrower_id}' not found")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_error(f"Failed to get borrower: {error_detail}")

    except Exception as e:
        print_error(f"Error: {str(e)}")


@borrower.command(name="block")
@click.argument("borrower_id")
@click.option("--reason", required=True, help="Reason for blocking")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def block_borrower(borrower_id: str, reason: str, api_url: str):
    """Block a borrower."""
    try:
        client = get_client(base_url=api_url)

        response = client.post(
            f"/api/v1/borrowers/{borrower_id}/block",
            params={"reason": reason},
        )

        if response.status_code == 200:
            console.print(f"\n[green]✓[/green] Borrower '{borrower_id}' has been blocked")
            console.print(f"  Reason: {reason}")
        elif response.status_code == 404:
            print_error(f"Borrower '{borrower_id}' not found")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_error(f"Failed to block borrower: {error_detail}")

    except Exception as e:
        print_error(f"Error: {str(e)}")


@borrower.command(name="unblock")
@click.argument("borrower_id")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def unblock_borrower(borrower_id: str, api_url: str):
    """Unblock a borrower."""
    try:
        client = get_client(base_url=api_url)

        response = client.post(f"/api/v1/borrowers/{borrower_id}/unblock")

        if response.status_code == 200:
            console.print(f"\n[green]✓[/green] Borrower '{borrower_id}' has been unblocked")
        elif response.status_code == 404:
            print_error(f"Borrower '{borrower_id}' not found")
        else:
            error_detail = response.json().get("detail", "Unknown error")
            print_error(f"Failed to unblock borrower: {error_detail}")

    except Exception as e:
        print_error(f"Error: {str(e)}")
