"""
Admin commands

Commands for system administration.
"""

from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from ..client import get_client
from ..utils.display import console, print_error


@click.group(name="admin")
def admin():
    """System administration commands."""
    pass


@admin.command(name="settings")
@click.option(
    "--set",
    "settings",
    multiple=True,
    help="Set a setting (format: key=value). Can be used multiple times.",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def manage_settings(settings: tuple, api_url: str):
    """
    View or update system settings.

    \b
    Usage:
        bcd-cli admin settings                           # View current settings
        bcd-cli admin settings --set loan_duration_days=21
        bcd-cli admin settings --set library_name="My Library" --set language=en
    """
    try:
        client = get_client(base_url=api_url)

        # If no updates, just display current settings
        if not settings:
            response = client.get("/api/v1/admin/settings")

            if response.status_code == 200:
                data = response.json()

                # Header
                console.print()
                console.print(
                    Panel(
                        "[bold cyan]⚙️ Paramètres système / System Settings[/bold cyan]",
                        style="cyan"
                    )
                )
                console.print()

                # Display settings in categories
                console.print("[bold]Bibliothèque / Library:[/bold]")
                console.print(f"  Nom / Name: {data.get('library_name', 'N/A')}")
                console.print(f"  Langue / Language: {data.get('language', 'N/A')}")
                console.print(f"  Année scolaire / Academic year: {data.get('academic_year', 'N/A')}")
                console.print()

                console.print("[bold]Prêts / Loans:[/bold]")
                console.print(f"  Durée de prêt / Loan duration: {data.get('loan_duration_days', 'N/A')} jours/days")
                console.print(f"  Limite élèves / Student limit: {data.get('loan_limit_student', 'N/A')}")
                console.print(f"  Limite enseignants / Teacher limit: {data.get('loan_limit_teacher', 'N/A')}")
                console.print(f"  Limite personnel / Staff limit: {data.get('loan_limit_staff', 'N/A')}")
                console.print(f"  Renouvellements max / Max renewals: {data.get('max_renewals', 'N/A')}")
                console.print()

                console.print("[bold]Retards / Overdue:[/bold]")
                console.print(f"  Délai de grâce / Grace period: {data.get('overdue_grace_period_days', 'N/A')} jours/days")
                console.print()

                console.print("[bold]Réservations / Holds:[/bold]")
                console.print(f"  Expiration réservation / Hold expiration: {data.get('hold_expiration_days', 'N/A')} jours/days")
                console.print()

                console.print("[bold]Format / Format:[/bold]")
                console.print(f"  Code-barres / Barcode type: {data.get('barcode_type', 'N/A')}")
                console.print(f"  Format ID / ID format: {data.get('id_format', 'N/A')}")
                console.print(f"  Regex validation: {data.get('id_validation_regex', 'N/A')}")

            else:
                print_error(f"Error retrieving settings: {response.text}")

        else:
            # Parse settings updates
            updates = {}
            for setting in settings:
                if "=" not in setting:
                    print_error(f"Invalid setting format: {setting}. Use key=value")
                    continue

                key, value = setting.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Try to convert value to appropriate type
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
                # Remove quotes if present
                elif value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                updates[key] = value

            if updates:
                # Send update request
                response = client.put(
                    "/api/v1/admin/settings",
                    json={"updates": updates}
                )

                if response.status_code == 200:
                    console.print("[green]Settings updated successfully[/green]")
                    console.print()

                    # Show updated settings
                    data = response.json()
                    for key, value in updates.items():
                        console.print(f"  {key}: [cyan]{value}[/cyan]")
                else:
                    print_error(f"Error updating settings: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()


@admin.command(name="backup")
@click.option(
    "--output",
    help="Custom output path for backup file (optional)",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def create_backup(output: Optional[str], api_url: str):
    """
    Create a database backup.

    The backup will be saved with a timestamp in ./backups/ directory
    or at a custom location if --output is specified.

    \b
    Usage:
        bcd-cli admin backup                    # Creates timestamped backup
        bcd-cli admin backup --output /path/to/backup.db
    """
    try:
        client = get_client(base_url=api_url)

        console.print()
        console.print("[yellow]Création de la sauvegarde / Creating database backup...[/yellow]")

        response = client.post("/api/v1/admin/backup")

        if response.status_code == 200:
            data = response.json()
            backup_info = data.get("backup", {})

            console.print()
            console.print(
                Panel(
                    "[bold green]Sauvegarde créée avec succès / Backup Created Successfully[/bold green]",
                    style="green"
                )
            )
            console.print()

            console.print(f"[bold]Fichier / File:[/bold] {backup_info.get('filename', 'N/A')}")
            console.print(f"[bold]Chemin / Path:[/bold] {backup_info.get('file_path', 'N/A')}")
            console.print(f"[bold]Taille / Size:[/bold] {backup_info.get('size_mb', 0)} MB")
            console.print(f"[bold]Date / Created:[/bold] {backup_info.get('created_at', 'N/A')}")

            console.print()
            console.print(
                "[dim]Conservez les sauvegardes dans un endroit sûr (disque externe, cloud) / "
                "Keep backups in a safe location (external drive, cloud)[/dim]"
            )

        else:
            print_error(f"Backup failed: {response.text}")
            raise SystemExit(1)

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise SystemExit(1)


@admin.command(name="list-backups")
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def list_backups(api_url: str):
    """
    List all available database backups with metadata.

    Shows backup files sorted by creation date (newest first).
    """
    try:
        client = get_client(base_url=api_url)

        response = client.get("/api/v1/admin/backups")

        if response.status_code == 200:
            data = response.json()
            backups = data.get("backups", [])
            db_info = data.get("database_info", {})

            console.print()
            console.print(
                Panel(
                    f"[bold cyan]Sauvegardes disponibles / Available Backups ({len(backups)})[/bold cyan]",
                    style="cyan"
                )
            )
            console.print()

            if not backups:
                console.print("[yellow]Aucune sauvegarde trouvée / No backups found[/yellow]")
                console.print()
                console.print("[dim]Créez une sauvegarde avec: bcd-cli admin backup[/dim]")
                return

            # Create table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Fichier / File", style="cyan")
            table.add_column("Taille / Size", justify="right")
            table.add_column("Date / Created")
            table.add_column("Âge / Age", justify="right")

            for backup in backups:
                age_days = backup.get("age_days", 0)
                age_color = "green" if age_days < 7 else ("yellow" if age_days < 30 else "red")

                table.add_row(
                    backup.get("filename", "N/A"),
                    f"{backup.get('size_mb', 0)} MB",
                    backup.get("created_at", "N/A")[:19],  # Trim microseconds
                    f"[{age_color}]{age_days} jours/days[/{age_color}]"
                )

            console.print(table)
            console.print()

            # Show current database size
            console.print(f"[dim]Base de données actuelle / Current database: {db_info.get('size_mb', 0)} MB[/dim]")

        else:
            print_error(f"Failed to list backups: {response.text}")
            raise SystemExit(1)

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise SystemExit(1)


@admin.command(name="restore")
@click.argument("backup_file")
@click.option(
    "--confirm",
    is_flag=True,
    help="Confirm restore operation (required)",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def restore_backup(backup_file: str, confirm: bool, api_url: str):
    """
    Restore database from a backup file.

    DANGEROUS OPERATION: This will overwrite the current database!

    A safety backup will be created automatically before restore.

    \b
    Usage:
        bcd-cli admin restore backups/bcd_backup_20260205_120000.db --confirm

    Args:
        backup_file: Path to the backup file to restore
    """
    try:
        # Double confirmation for safety - check BEFORE creating client
        if not confirm:
            console.print()
            console.print("[bold red]ATTENTION / WARNING![/bold red]")
            console.print()
            console.print("Cette opération va écraser la base de données actuelle!")
            console.print("This operation will overwrite the current database!")
            console.print()
            console.print("[yellow]Utilisez --confirm pour confirmer / Use --confirm to proceed[/yellow]")
            return

        client = get_client(base_url=api_url)

        # Extra confirmation prompt
        console.print()
        console.print("[bold red]RESTAURATION DE LA BASE DE DONNÉES / DATABASE RESTORE[/bold red]")
        console.print()
        console.print(f"Fichier source / Source file: [cyan]{backup_file}[/cyan]")
        console.print()
        console.print("[yellow]Une sauvegarde de sécurité sera créée automatiquement.[/yellow]")
        console.print("[yellow]A safety backup will be created automatically.[/yellow]")
        console.print()

        if not click.confirm("Confirmer la restauration / Confirm restore?"):
            console.print("[yellow]Opération annulée / Operation cancelled[/yellow]")
            return

        console.print()
        console.print("[yellow]Restauration en cours / Restoring database...[/yellow]")

        response = client.post(
            "/api/v1/admin/restore",
            params={"backup_file": backup_file, "confirm": True}
        )

        if response.status_code == 200:
            data = response.json()

            console.print()
            console.print(
                Panel(
                    "[bold green]Restauration réussie / Restore Successful[/bold green]",
                    style="green"
                )
            )
            console.print()

            console.print(f"[bold]Restauré depuis / Restored from:[/bold] {data.get('restored_from', 'N/A')}")
            console.print()
            console.print(f"[yellow]{data.get('warning', '')}[/yellow]")
            console.print()
            console.print("[green]La base de données a été restaurée avec succès.[/green]")
            console.print("[green]The database has been restored successfully.[/green]")

        else:
            error_data = response.json()
            print_error(f"Restore failed: {error_data.get('detail', response.text)}")
            raise SystemExit(1)

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise SystemExit(1)


@admin.command(name="archive")
@click.option(
    "--older-than",
    default=5,
    type=int,
    help="Archive transactions older than N years (default: 5)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be archived without actually archiving",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show archive statistics only",
)
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def archive_transactions(older_than: int, dry_run: bool, stats: bool, api_url: str):
    """
    Archive old circulation transactions to prevent database bloat.

    Without archiving, the circulation_transaction table grows to 180k+ rows
    over 10 years, causing performance degradation. This command moves old
    transactions (default: 5+ years old) to an archive table.

    \b
    Usage:
        bcd-cli admin archive --stats                    # Show archive statistics
        bcd-cli admin archive --dry-run                  # Preview what would be archived
        bcd-cli admin archive                            # Archive transactions >5 years
        bcd-cli admin archive --older-than 3             # Archive transactions >3 years

    Args:
        older_than: Archive transactions older than this many years
        dry_run: Preview mode - don't actually archive
        stats: Show archive statistics
    """
    try:
        client = get_client(base_url=api_url)

        # Show archive statistics
        if stats:
            response = client.get("/api/v1/admin/archive/stats")

            if response.status_code == 200:
                data = response.json()

                console.print()
                console.print(
                    Panel(
                        "[bold cyan]Statistiques d'archivage / Archive Statistics[/bold cyan]",
                        style="cyan"
                    )
                )
                console.print()

                if data.get("total_archived", 0) == 0:
                    console.print("[yellow]Aucune transaction archivée / No archived transactions[/yellow]")
                else:
                    console.print(f"[bold]Total archivé / Total archived:[/bold] {data.get('total_archived', 0)} transactions")
                    console.print(f"[bold]Taille estimée / Estimated size:[/bold] {data.get('estimated_size_mb', 0)} MB")
                    console.print()
                    console.print(f"[dim]Première transaction / Oldest transaction: {data.get('oldest_transaction_date', 'N/A')}[/dim]")
                    console.print(f"[dim]Dernière transaction / Newest transaction: {data.get('newest_transaction_date', 'N/A')}[/dim]")
                    console.print()
                    console.print(f"[dim]Premier archivage / First archived: {data.get('first_archived_at', 'N/A')}[/dim]")
                    console.print(f"[dim]Dernier archivage / Last archived: {data.get('last_archived_at', 'N/A')}[/dim]")

                console.print()
            else:
                print_error(f"Failed to get archive stats: {response.text}")
                raise SystemExit(1)
            return

        # Archive transactions
        mode_label = "[yellow]MODE SIMULATION / DRY RUN MODE[/yellow]" if dry_run else "[green]MODE ARCHIVAGE / ARCHIVE MODE[/green]"

        console.print()
        console.print(
            Panel(
                f"[bold]Archivage des transactions / Archive Transactions[/bold]\n{mode_label}",
                style="cyan" if dry_run else "green"
            )
        )
        console.print()

        if not dry_run:
            console.print(f"[yellow]Ceci va archiver les transactions de plus de {older_than} ans.[/yellow]")
            console.print(f"[yellow]This will archive transactions older than {older_than} years.[/yellow]")
            console.print()

            if not click.confirm("Continuer / Continue?"):
                console.print("[yellow]Opération annulée / Operation cancelled[/yellow]")
                return
            console.print()

        response = client.post(
            f"/api/v1/admin/archive?older_than_years={older_than}&dry_run={str(dry_run).lower()}"
        )

        if response.status_code == 200:
            data = response.json()

            if data.get("archived_count", 0) == 0:
                console.print("[green]Aucune transaction à archiver / No transactions to archive[/green]")
                console.print()
                console.print(f"[dim]Toutes les transactions sont récentes (< {older_than} ans).[/dim]")
                console.print(f"[dim]All transactions are recent (< {older_than} years).[/dim]")
            else:
                console.print()
                if dry_run:
                    console.print("[bold yellow]Aperçu de l'archivage / Archive Preview:[/bold yellow]")
                else:
                    console.print("[bold green]Archivage terminé / Archive Completed:[/bold green]")
                console.print()

                console.print(f"[bold]Transactions archivées / Archived:[/bold] {data.get('archived_count', 0)}")
                console.print(f"[bold]Réduction de taille / Size reduction:[/bold] ~{data.get('size_reduction_estimate_mb', 0)} MB")
                console.print()
                console.print("[dim]Plage de dates / Date range:[/dim]")
                console.print(f"[dim]  De / From: {data.get('oldest_date', 'N/A')}[/dim]")
                console.print(f"[dim]  À / To: {data.get('newest_date', 'N/A')}[/dim]")

                if dry_run:
                    console.print()
                    console.print("[yellow]Exécutez sans --dry-run pour archiver réellement.[/yellow]")
                    console.print("[yellow]Run without --dry-run to actually archive.[/yellow]")

            console.print()

        else:
            error_data = response.json()
            print_error(f"Archive failed: {error_data.get('detail', response.text)}")
            raise SystemExit(1)

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise SystemExit(1)


@admin.command(name="health")
@click.option(
    "--api-url",
    default="http://localhost:8888",
    help="API server URL",
    envvar="BCD_API_URL",
)
def health_check(api_url: str):
    """
    Check system health and display statistics.
    """
    try:
        client = get_client(base_url=api_url)

        response = client.get("/api/v1/admin/health")

        if response.status_code == 200:
            data = response.json()

            console.print()
            console.print(
                Panel(
                    "[bold green]Santé du système / System Health[/bold green]",
                    style="green"
                )
            )
            console.print()

            status_color = "green" if data.get("status") == "healthy" else "red"
            console.print(f"[bold]Statut / Status:[/bold] [{status_color}]{data.get('status', 'unknown')}[/{status_color}]")
            console.print(f"[bold]Base de données / Database:[/bold] {data.get('database', 'N/A')}")

            counts = data.get("counts", {})
            if counts:
                console.print()
                console.print("[bold]Statistiques / Statistics:[/bold]")
                console.print(f"  Emprunteurs / Borrowers: {counts.get('borrowers', 0)}")
                console.print(f"  Notices bibliographiques / Bibliographic records: {counts.get('bibliographic_records', 0)}")
                console.print(f"  Exemplaires / Items: {counts.get('items', 0)}")
                console.print(f"  Transactions / Circulations: {counts.get('circulations', 0)}")

        else:
            print_error(f"Health check failed: {response.text}")

    except Exception as e:
        print_error(f"Erreur / Error: {str(e)}")
        raise click.Abort()
