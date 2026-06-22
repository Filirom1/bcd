#!/usr/bin/env python3
"""
BCD CLI - Main entry point

Command-line interface for the BCD library management system.
"""

import os
import sys

import click

from src.shared.version import __version__


@click.group()
@click.version_option(version=__version__, prog_name="bcd-cli")
@click.option(
    "--auth-username",
    envvar="BCD_AUTH_USERNAME",
    help="Username for HTTP authentication (or set BCD_AUTH_USERNAME env var)",
)
@click.option(
    "--auth-password",
    envvar="BCD_AUTH_PASSWORD",
    help="Password for HTTP authentication (or set BCD_AUTH_PASSWORD env var)",
)
@click.pass_context
def cli(ctx, auth_username, auth_password):
    """
    BCD Library Management System

    Command-line interface for managing library circulation, cataloging,
    and borrower operations.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store auth credentials in context for subcommands
    ctx.obj["auth_username"] = auth_username
    ctx.obj["auth_password"] = auth_password

    # Set environment variables so get_client() can pick them up
    # This allows existing commands to work without modification
    if auth_username:
        os.environ["BCD_AUTH_USERNAME"] = auth_username
    if auth_password:
        os.environ["BCD_AUTH_PASSWORD"] = auth_password


@cli.command()
def version():
    """Show version information."""
    click.echo(f"BCD CLI v{__version__}")
    click.echo("School Library Management System")


# Import and register command groups
def register_commands():
    """Register all command modules."""
    try:
        from .commands import (
            admin,
            borrower,
            catalog,
            checkout,
            config,
            hold,
            item,
            renew,
            report,
            return_cmd,
        )

        # Register commands
        cli.add_command(checkout.checkout)
        cli.add_command(return_cmd.return_items)
        cli.add_command(renew.renew)
        cli.add_command(catalog.catalog)
        cli.add_command(borrower.borrower)
        cli.add_command(item.item)
        cli.add_command(hold.hold)
        cli.add_command(report.report)
        cli.add_command(admin.admin)
        cli.add_command(config.config)

    except ImportError:
        # Commands not yet implemented - graceful degradation
        pass


# Register commands on import
register_commands()


def main():
    """Main entry point for the CLI."""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\n\nOperation cancelled by user.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
