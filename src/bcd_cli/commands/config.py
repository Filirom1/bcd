"""
Config commands

Commands for managing CLI configuration.
"""

import json
from pathlib import Path
from typing import Any

import click

from ..utils.display import console, print_error

# Default config location
CONFIG_DIR = Path.home() / ".bcd"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "api_url": "http://localhost:8888",
    "language": "fr",
    "timeout": 30,
}


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


@click.group(name="config")
def config():
    """Manage CLI configuration."""
    pass


@config.command(name="show")
def show_config():
    """Display current configuration."""
    try:
        cfg = load_config()

        console.print()
        console.print("[bold cyan]⚙️ Configuration BCD CLI[/bold cyan]")
        console.print()

        console.print(f"[bold]Fichier config / Config file:[/bold] {CONFIG_FILE}")
        console.print()

        console.print("[bold]Paramètres / Settings:[/bold]")
        for key, value in cfg.items():
            console.print(f"  {key}: [cyan]{value}[/cyan]")

    except Exception as e:
        print_error(f"Error loading config: {str(e)}")
        raise click.Abort()


@config.command(name="set")
@click.argument("key", required=True)
@click.argument("value", required=True)
def set_config(key: str, value: str):
    """
    Set a configuration value.

    \b
    Usage:
        bcd config set api_url http://localhost:8888
        bcd config set language en
        bcd config set timeout 60
    """
    try:
        cfg = load_config()

        # Convert value to appropriate type
        typed_value: Any = value
        if value.lower() in ("true", "false"):
            typed_value = value.lower() == "true"
        elif value.isdigit():
            typed_value = int(value)
        elif value.replace(".", "", 1).isdigit():
            typed_value = float(value)

        cfg[key] = typed_value
        save_config(cfg)

        console.print(f"[green]✅ Configuration updated:[/green] {key} = [cyan]{typed_value}[/cyan]")

    except Exception as e:
        print_error(f"Error setting config: {str(e)}")
        raise click.Abort()


@config.command(name="reset")
@click.confirmation_option(prompt="Reset all configuration to defaults?")
def reset_config():
    """Reset configuration to default values."""
    try:
        save_config(DEFAULT_CONFIG.copy())
        console.print("[green]✅ Configuration reset to defaults[/green]")

    except Exception as e:
        print_error(f"Error resetting config: {str(e)}")
        raise click.Abort()


@config.command(name="edit")
def edit_config():
    """Open configuration file in default editor."""
    try:
        import os
        import subprocess

        # Ensure config file exists
        if not CONFIG_FILE.exists():
            save_config(DEFAULT_CONFIG.copy())

        # Get editor
        editor = os.environ.get("EDITOR", "nano")

        # Open in editor
        subprocess.run([editor, str(CONFIG_FILE)])

    except Exception as e:
        print_error(f"Error editing config: {str(e)}")
        raise click.Abort()
