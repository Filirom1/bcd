"""
Catalog command

Catalog management including import, search, and add operations.
"""

import click
from pathlib import Path
from typing import Optional
from ..client import get_client
from ..utils.display import (
    console,
    print_header,
    print_error,
    print_warning,
)


@click.group(name="catalog")
def catalog():
    """
    Catalog management commands.

    \b
    Examples:
        bcd-cli catalog transform catalog.csv catalog_dc.csv
        bcd-cli catalog import-dc catalog_dc.csv
        bcd-cli catalog search --title "Harry Potter"
        bcd-cli catalog add --isbn 978-2-8006-8734-6
    """
    pass


@catalog.command(name="search")
@click.option("--title", help="Search by title")
@click.option("--author", help="Search by author")
@click.option("--isbn", help="Search by ISBN")
@click.option("--category", help="Filter by category")
@click.option("--genre", help="Filter by genre")
@click.option("--limit", default=20, help="Maximum results to show")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def search(
    title: Optional[str],
    author: Optional[str],
    isbn: Optional[str],
    category: Optional[str],
    genre: Optional[str],
    limit: int,
    api_url: str,
):
    """
    Search bibliographic records.

    \b
    Examples:
        bcd-cli catalog search --title "Harry Potter"
        bcd-cli catalog search --author "Rowling"
        bcd-cli catalog search --isbn 978-2-8006-8734-6
        bcd-cli catalog search --category "Fiction" --genre "Album"
    """
    try:
        client = get_client(base_url=api_url)

        print_header("Catalog Search")

        # Build query parameters
        params = {}
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        if isbn:
            params["isbn"] = isbn
        if category:
            params["category"] = category
        if genre:
            params["genre"] = genre
        params["limit"] = limit

        # Search
        response = client.get("/api/v1/catalog/bibliographic/search", params=params)

        if response.status_code != 200:
            print_error(f"Search failed: {response.status_code}")
            raise click.Abort()

        data = response.json()
        records = data.get("items", [])
        total = data.get("total", 0)

        console.print(f"[cyan]Found {total} records[/cyan]")
        console.print()

        if not records:
            console.print("[yellow]No records found[/yellow]")
            return

        # Display results
        from rich.table import Table

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID", width=6, style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Author(s)", style="green")
        table.add_column("ISBN", width=15, style="yellow")
        table.add_column("Items", width=6, justify="right", style="magenta")

        for record in records:
            authors = ", ".join(record.get("authors", []))[:40]
            isbn_str = record.get("isbn", "") or ""
            items_count = record.get("total_items", 0)

            table.add_row(
                str(record["id"]),
                record["title"][:50],
                authors,
                isbn_str,
                str(items_count),
            )

        console.print(table)

        if total > limit:
            console.print()
            console.print(f"[yellow]Showing {len(records)} of {total} results[/yellow]")
            console.print(f"[dim]Use --limit to show more results[/dim]")

    except click.Abort:
        raise
    except Exception as e:
        print_error(f"Search failed: {str(e)}")
        raise click.Abort()


@catalog.command(name="transform")
@click.argument("input_file", type=click.Path(exists=True))
@click.argument("output_file", type=click.Path())
@click.option(
    "--format",
    type=click.Choice(["dublin-core"], case_sensitive=False),
    default="dublin-core",
    help="Target format for transformation",
)
def transform_csv(input_file: str, output_file: str, format: str):
    """
    Transform BCD CSV to standard format (Dublin Core).

    Converts custom BCD CSV format to Dublin Core standard format for
    interoperability with other library systems.

    \b
    Examples:
        bcd-cli catalog transform catalog.csv catalog_dc.csv
        bcd-cli catalog transform catalog.csv catalog_dc.csv --format dublin-core
    """
    try:
        from pathlib import Path
        from src.bcd_api.services.csv_transform import transform_bcd_to_dublin_core

        print_header("CSV Transformation")

        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            print_error(f"Input file not found: {input_file}")
            raise click.Abort()

        console.print(f"[cyan]Input:[/cyan] {input_path.name}")
        console.print(f"[cyan]Output:[/cyan] {output_path.name}")
        console.print(f"[cyan]Format:[/cyan] {format}")
        console.print()

        # Read input file
        with open(input_path, "r", encoding="cp1252") as f:
            bcd_csv = f.read()

        # Transform
        console.print("[cyan]Transforming...[/cyan]")
        dc_csv = transform_bcd_to_dublin_core(bcd_csv)

        # Write output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(dc_csv)

        # Count rows
        dc_lines = len(dc_csv.strip().split("\n"))
        console.print()
        console.print("[bold green]Transformation Complete[/bold green]")
        console.print(f"[green]Created {dc_lines - 1} rows in Dublin Core format[/green]")
        console.print()
        console.print(f"[dim]Output saved to: {output_path}[/dim]")

    except click.Abort:
        raise
    except Exception as e:
        print_error(f"Transformation failed: {str(e)}")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
        raise click.Abort()


@catalog.command(name="import-dc")
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt (for automated/non-interactive use)",
)
def import_dublin_core(file_path: str, api_url: str, yes: bool):
    """
    Import bibliographic records from Dublin Core CSV file.

    Dublin Core is a standard metadata format used by libraries worldwide.
    Use 'bcd-cli catalog transform' to convert BCD CSV to Dublin Core first.

    \b
    Dublin Core CSV Format (comma-separated):
    Required: dc.title, dc.identifier
    Optional: dc.creator, dc.subject, dc.description, dc.publisher,
              dc.contributor, dc.date, dc.type, dc.format, etc.

    \b
    Examples:
        bcd-cli catalog import-dc catalog_dublin_core.csv
        bcd-cli catalog import-dc ~/Downloads/catalog_dc.csv --api-url http://server:8000
    """
    try:
        client = get_client(base_url=api_url)

        print_header("Dublin Core Import")

        # Read file
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            print_error(f"File not found: {file_path}")
            raise click.Abort()

        file_size = file_path_obj.stat().st_size
        console.print(f"[cyan]File:[/cyan] {file_path_obj.name}")
        console.print(f"[cyan]Size:[/cyan] {file_size:,} bytes")
        console.print(f"[cyan]Format:[/cyan] Dublin Core CSV")
        console.print()

        # Confirm import (unless --yes flag)
        if not yes:
            console.print("[bold yellow]Warning:[/bold yellow] This will import data into the database.")
            if not click.confirm("Do you want to proceed?", default=True):
                console.print("[yellow]Import cancelled[/yellow]")
                return

        console.print()
        console.print("[cyan]Importing Dublin Core CSV...[/cyan]")
        console.print()

        # Upload file
        with open(file_path_obj, "rb") as f:
            files = {"file": (file_path_obj.name, f, "text/csv")}
            response = client.post("/api/v1/catalog/import-dc", files=files)

        if response.status_code != 200:
            print_error(f"Import failed: {response.status_code}")
            if response.text:
                console.print(f"[red]{response.text}[/red]")
            raise click.Abort()

        result = response.json()

        # Display results
        console.print("[bold green]Dublin Core Import Complete[/bold green]")
        console.print()

        # Summary table
        from rich.table import Table

        table = Table(title="Import Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Bibliographic Records Created", str(result["records_created"]))
        table.add_row("Items Created", str(result["items_created"]))
        table.add_row("Records Skipped (duplicates)", str(result["records_skipped"]))
        table.add_row("Items Skipped (duplicates)", str(result["items_skipped"]))
        table.add_row("Total Rows Processed", str(result["total_rows"]))

        console.print(table)
        console.print()

        # Errors
        if result.get("errors"):
            print_warning(f"{len(result['errors'])} errors occurred during import")
            console.print()

            error_table = Table(title="Errors", show_header=True, header_style="bold red")
            error_table.add_column("Row", style="yellow", width=6)
            error_table.add_column("Error", style="red")

            for error in result["errors"][:10]:  # Show first 10 errors
                error_table.add_row(str(error["row"]), error["error"])

            if len(result["errors"]) > 10:
                error_table.add_row("...", f"and {len(result['errors']) - 10} more errors")

            console.print(error_table)
        else:
            console.print("[green]No errors[/green]")

    except click.Abort:
        raise
    except Exception as e:
        print_error(f"Import failed: {str(e)}")
        raise click.Abort()


@catalog.command(name="add")
@click.option("--isbn", help="ISBN for BNF lookup")
@click.option("--title", help="Title (for manual entry)")
@click.option("--author", help="Author (for manual entry)")
@click.option("--publisher", help="Publisher")
@click.option("--year", type=int, help="Publication year")
@click.option("--category", help="Category")
@click.option("--genre", help="Genre")
@click.option(
    "--api-url",
    default="http://localhost:8000",
    help="API server URL",
    envvar="BCD_API_URL",
)
def add(
    isbn: Optional[str],
    title: Optional[str],
    author: Optional[str],
    publisher: Optional[str],
    year: Optional[int],
    category: Optional[str],
    genre: Optional[str],
    api_url: str,
):
    """
    Add a new bibliographic record.

    \b
    Examples:
        # With BNF ISBN lookup
        bcd-cli catalog add --isbn 978-2-8006-8734-6

        # Manual entry
        bcd-cli catalog add --title "Test Book" --author "Smith, John" --year 2024
    """
    try:
        client = get_client(base_url=api_url)

        print_header("Add Bibliographic Record")

        # Validate input
        if not isbn and not title:
            print_error("Either --isbn or --title is required")
            raise click.Abort()

        # Prepare data
        data = {}
        if isbn:
            data["isbn"] = isbn
        if title:
            data["title"] = title
        else:
            data["title"] = "Placeholder"  # Will be replaced by BNF data
        if author:
            data["authors"] = [author]
        if publisher:
            data["publisher"] = publisher
        if year:
            data["publication_year"] = year
        if category:
            data["category"] = category
        if genre:
            data["genre"] = genre

        # Determine if ISBN lookup should be used
        isbn_lookup = bool(isbn)

        console.print(f"[cyan]Mode:[/cyan] {'ISBN Lookup' if isbn_lookup else 'Manual Entry'}")
        if isbn_lookup:
            console.print(f"[cyan]ISBN:[/cyan] {isbn}")
        console.print()

        # Create record
        response = client.post(
            f"/api/v1/catalog/bibliographic?isbn_lookup={isbn_lookup}", json=data
        )

        if response.status_code != 201:
            print_error(f"Failed to create record: {response.status_code}")
            if response.text:
                console.print(f"[red]{response.text}[/red]")
            raise click.Abort()

        record = response.json()

        # Display result
        console.print("[bold green]Record Created[/bold green]")
        console.print()
        console.print(f"[cyan]ID:[/cyan] {record['id']}")
        console.print(f"[cyan]Title:[/cyan] {record['title']}")
        if record.get("authors"):
            console.print(f"[cyan]Author(s):[/cyan] {', '.join(record['authors'])}")
        if record.get("publisher"):
            console.print(f"[cyan]Publisher:[/cyan] {record['publisher']}")
        if record.get("publication_year"):
            console.print(f"[cyan]Year:[/cyan] {record['publication_year']}")
        if record.get("isbn"):
            console.print(f"[cyan]ISBN:[/cyan] {record['isbn']}")

    except click.Abort:
        raise
    except Exception as e:
        print_error(f"Failed to add record: {str(e)}")
        raise click.Abort()
