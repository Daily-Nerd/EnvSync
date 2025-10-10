"""Diff command for TripWire CLI."""

import json
import sys
from pathlib import Path

import click
from rich.table import Table

from tripwire.branding import LOGO_BANNER
from tripwire.cli.utils.console import console
from tripwire.config.models import ConfigValue


@click.command()
@click.argument("source1")
@click.argument("source2")
@click.option(
    "--format",
    type=click.Choice(["table", "json", "summary"]),
    default="table",
    help="Output format for differences",
)
@click.option(
    "--show-secrets/--hide-secrets",
    default=False,
    help="Show/hide values that appear to be secrets",
)
def diff(source1: str, source2: str, format: str, show_secrets: bool) -> None:
    """Compare two configuration sources.

    Compares configuration between two files (.env or .toml) and displays
    the differences. Useful for comparing development vs production configs,
    or checking configuration drift between environments.

    Examples:

        \b
        # Compare .env files
        tripwire diff .env .env.prod

        \b
        # Compare .env with TOML config
        tripwire diff .env pyproject.toml

        \b
        # Compare with JSON output
        tripwire diff .env .env.prod --format=json

        \b
        # Show secret values (use with caution!)
        tripwire diff .env .env.prod --show-secrets
    """
    from tripwire.config.repository import ConfigRepository

    console.print(f"[cyan]{LOGO_BANNER}[/cyan]")
    console.print(f"[bold cyan]Comparing configurations:[/bold cyan] {source1} vs {source2}\n")

    # Validate files exist
    if not Path(source1).exists():
        console.print(f"[red][ERROR][/red] File not found: {source1}")
        sys.exit(1)

    if not Path(source2).exists():
        console.print(f"[red][ERROR][/red] File not found: {source2}")
        sys.exit(1)

    try:
        # Load both sources
        with console.status(f"Loading {source1}..."):
            repo1 = ConfigRepository.from_file(source1).load()

        with console.status(f"Loading {source2}..."):
            repo2 = ConfigRepository.from_file(source2).load()

        # Compute diff
        diff_result = repo1.diff(repo2)

        # Display results based on format
        if format == "json":
            output = {
                "added": {k: v.raw_value for k, v in diff_result.added.items()},
                "removed": {k: v.raw_value for k, v in diff_result.removed.items()},
                "modified": {
                    k: {"old": old.raw_value, "new": new.raw_value} for k, (old, new) in diff_result.modified.items()
                },
                "unchanged": {k: v.raw_value for k, v in diff_result.unchanged.items()},
            }
            console.print(json.dumps(output, indent=2))

        elif format == "summary":
            if not diff_result.has_changes:
                console.print("[green]Configurations are identical[/green]")
            else:
                console.print(f"[bold cyan]Summary:[/bold cyan] {diff_result.summary()}\n")

                if diff_result.added:
                    console.print(f"[green]Added:[/green] {len(diff_result.added)} variables")
                    for key in sorted(diff_result.added.keys()):
                        console.print(f"  + {key}")

                if diff_result.removed:
                    console.print(f"\n[red]Removed:[/red] {len(diff_result.removed)} variables")
                    for key in sorted(diff_result.removed.keys()):
                        console.print(f"  - {key}")

                if diff_result.modified:
                    console.print(f"\n[yellow]Modified:[/yellow] {len(diff_result.modified)} variables")
                    for key in sorted(diff_result.modified.keys()):
                        console.print(f"  ~ {key}")

        else:  # table format (default)
            if not diff_result.has_changes:
                console.print("[green][OK][/green] Configurations are identical")
                return

            # Create table showing differences
            table = Table(title=f"Configuration Differences: {Path(source1).name} vs {Path(source2).name}")
            table.add_column("Status", style="bold", width=10)
            table.add_column("Variable", style="cyan")
            table.add_column(Path(source1).name, style="magenta")
            table.add_column(Path(source2).name, style="blue")

            def mask_secret(value: ConfigValue, show: bool) -> str:
                """Mask secret values unless show_secrets is True."""
                if value.metadata.is_secret and not show:
                    return "[dim]<secret hidden>[/dim]"
                # Truncate long values
                raw = value.raw_value
                if len(raw) > 50:
                    return raw[:47] + "..."
                return raw

            # Add rows for each change type
            for key in sorted(diff_result.added.keys()):
                value = diff_result.added[key]
                table.add_row(
                    "[green]+ Added[/green]",
                    key,
                    "",
                    mask_secret(value, show_secrets),
                )

            for key in sorted(diff_result.removed.keys()):
                value = diff_result.removed[key]
                table.add_row(
                    "[red]- Removed[/red]",
                    key,
                    mask_secret(value, show_secrets),
                    "",
                )

            for key in sorted(diff_result.modified.keys()):
                old_val, new_val = diff_result.modified[key]
                table.add_row(
                    "[yellow]~ Modified[/yellow]",
                    key,
                    mask_secret(old_val, show_secrets),
                    mask_secret(new_val, show_secrets),
                )

            console.print(table)
            console.print(f"\n[dim]{diff_result.summary()}[/dim]")

            # Warn if secrets were hidden
            has_secrets = any(
                v.metadata.is_secret for v in list(diff_result.added.values()) + list(diff_result.removed.values())
            ) or any(old.metadata.is_secret or new.metadata.is_secret for old, new in diff_result.modified.values())

            if has_secrets and not show_secrets:
                console.print("\n[yellow][WARNING][/yellow] Some values appear to be secrets and were hidden.")
                console.print("[yellow][WARNING][/yellow] Use --show-secrets to display them (use with caution!)")

    except ValueError as e:
        console.print(f"[red][ERROR][/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red][ERROR][/red] Failed to compare configurations: {e}")
        sys.exit(1)


__all__ = ["diff"]
