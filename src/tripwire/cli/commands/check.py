"""Check command for TripWire CLI."""

import json
import sys
from pathlib import Path

import click
from rich.table import Table

from tripwire.branding import get_status_icon
from tripwire.cli.utils.console import console


@click.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to check",
)
@click.option(
    "--example",
    type=click.Path(exists=True),
    default=".env.example",
    help=".env.example file to compare against",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with error if differences found",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def check(env_file: str | Path, example: str | Path, strict: bool, output_json: bool) -> None:
    """Check .env file for missing or extra variables.

    Compares your .env file against .env.example to detect drift
    and ensure all required variables are set.
    """
    from tripwire.parser import compare_env_files

    env_path = Path(env_file)
    example_path = Path(example)

    # Validate files exist
    if not example_path.exists():
        console.print(f"[red]Error:[/red] {example} not found")
        sys.exit(1)

    # Compare files
    missing, extra, common = compare_env_files(env_path, example_path)

    # JSON output mode
    if output_json:
        result = {
            "status": "ok" if not missing and not extra else "drift",
            "missing": missing,
            "extra": extra,
            "common": common,
        }
        print(json.dumps(result, indent=2))

        if strict and (missing or extra):
            sys.exit(1)
        return

    # Human-readable output
    console.print(f"\nComparing [cyan]{env_file}[/cyan] against [cyan]{example}[/cyan]\n")

    has_issues = False

    # Report missing variables
    if missing:
        has_issues = True
        table = Table(title="Missing Variables", show_header=True, header_style="bold red")
        table.add_column("Variable", style="red")
        table.add_column("Status", style="red")

        for var in missing:
            table.add_row(var, "Not set in .env")

        console.print(table)
        console.print()

    # Report extra variables
    if extra:
        has_issues = True
        table = Table(title="Extra Variables", show_header=True, header_style="bold yellow")
        table.add_column("Variable", style="yellow")
        table.add_column("Status", style="yellow")

        for var in extra:
            table.add_row(var, "Not in .env.example")

        console.print(table)
        console.print()

    # Summary
    if has_issues:
        console.print(f"[yellow]Found {len(missing)} missing and {len(extra)} extra variable(s)[/yellow]")

        if missing:
            console.print("\nTo add missing variables:")
            console.print("  [cyan]tripwire sync[/cyan]")

        if strict:
            sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} No drift detected - .env is in sync with .env.example")
        console.print(f"  {len(common)} variable(s) present in both files")


__all__ = ["check"]
