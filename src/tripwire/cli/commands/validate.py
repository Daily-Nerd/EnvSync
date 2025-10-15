"""Validate command for TripWire CLI."""

import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.table import Table

from tripwire.branding import get_status_icon
from tripwire.cli.utils.console import console


@click.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to validate",
)
def validate(env_file: str | Path) -> None:
    """Validate environment variables without running app.

    Loads and validates all environment variables to ensure they
    meet requirements before starting the application.
    """
    from tripwire.scanner import deduplicate_variables, scan_directory

    env_path = Path(env_file)

    if not env_path.exists():
        console.print(f"[red]Error:[/red] {env_file} not found")
        sys.exit(1)

    console.print(f"[yellow]Validating {env_file}...[/yellow]\n")

    # Scan code for required variables
    console.print("Scanning code for environment variable requirements...")
    try:
        variables = scan_directory(Path.cwd())
    except Exception as e:
        console.print(f"[red]Error scanning code:[/red] {e}")
        sys.exit(1)

    if not variables:
        console.print("[yellow]No environment variables found in code[/yellow]")
        console.print("Nothing to validate")
        return

    # Load the env file (override=True to ensure test .env files take precedence)
    load_dotenv(env_path, override=True)

    # Check each required variable
    unique_vars = deduplicate_variables(variables)
    required_vars = [v for v in unique_vars.values() if v.required]
    optional_vars = [v for v in unique_vars.values() if not v.required]

    console.print(
        f"Found {len(unique_vars)} variable(s): {len(required_vars)} required, {len(optional_vars)} optional\n"
    )

    missing = []

    for var in required_vars:
        if not os.getenv(var.name):
            missing.append(var.name)

    # Display results
    if missing:
        table = Table(title="Missing Required Variables", show_header=True, header_style="bold red")
        table.add_column("Variable", style="red")
        table.add_column("Type", style="yellow")

        for var_name in missing:
            var = unique_vars[var_name]
            table.add_row(var_name, var.var_type)

        console.print(table)
        console.print()
        status = get_status_icon("invalid")
        console.print(f"{status} [red]Validation failed:[/red] {len(missing)} required variable(s) missing")
        console.print("\nAdd these variables to your .env file")
        sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} All required variables are set")
        console.print(f"  {len(required_vars)} required variable(s) validated")
        if optional_vars:
            console.print(f"  {len(optional_vars)} optional variable(s) available")


__all__ = ["validate"]
