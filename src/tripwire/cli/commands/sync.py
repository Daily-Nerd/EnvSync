"""Sync command for TripWire CLI."""

import sys
from pathlib import Path

import click
from dotenv import dotenv_values
from rich.table import Table

from tripwire.branding import get_status_icon
from tripwire.cli.utils.console import console


@click.command()
@click.option(
    "--env-file",
    type=click.Path(),
    default=".env",
    help=".env file to sync",
)
@click.option(
    "--example",
    type=click.Path(exists=True),
    default=".env.example",
    help=".env.example to sync from",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show changes without applying",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Confirm each change",
)
def sync(env_file: str | Path, example: str | Path, dry_run: bool, interactive: bool) -> None:
    """Synchronize .env with .env.example.

    Updates your .env file to match the structure of .env.example,
    adding missing variables and optionally removing extra ones.
    """
    from tripwire.parser import compare_env_files, merge_env_files, parse_env_file

    env_path = Path(env_file)
    example_path = Path(example)

    # Validate example file exists
    if not example_path.exists():
        console.print(f"[red]Error:[/red] {example} not found")
        sys.exit(1)

    # Compare files
    missing, extra, _ = compare_env_files(env_path, example_path)

    if not missing and not extra:
        status = get_status_icon("valid")
        console.print(f"{status} Already in sync - no changes needed")
        return

    console.print(f"\nSynchronizing [cyan]{env_file}[/cyan] with [cyan]{example}[/cyan]\n")

    # Show what will be done
    changes_made = False

    if missing:
        console.print(f"[yellow]Will add {len(missing)} missing variable(s):[/yellow]")
        for var in missing:
            console.print(f"  + {var}")
        console.print()
        changes_made = True

    if extra:
        console.print(f"[blue]Found {len(extra)} extra variable(s) (will be kept):[/blue]")
        for var in extra:
            console.print(f"  ~ {var}")
        console.print()

    if not changes_made:
        console.print("[green]No changes needed[/green]")
        return

    if dry_run:
        console.print("[yellow]Dry run - no changes applied[/yellow]")
        console.print("Run without --dry-run to apply changes")
        return

    if interactive:
        if not click.confirm("Apply these changes?"):
            console.print("Sync cancelled")
            return

    # Get values from example file
    example_vars = parse_env_file(example_path)
    new_vars = {var: example_vars[var] for var in missing}

    # Merge into env file
    merged_content = merge_env_files(env_path, new_vars, preserve_existing=True)

    # Write updated file
    env_path.write_text(merged_content)

    console.print(f"[green][OK][/green] Synchronized {env_file}")
    console.print(f"  Added {len(missing)} variable(s)")
    console.print("\n[yellow]Note:[/yellow] Fill in values for new variables in .env")


__all__ = ["sync"]
