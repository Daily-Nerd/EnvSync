"""Plugin list command for TripWire CLI."""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from tripwire.plugins import PluginInstaller, PluginRegistryClient

console = Console()


@click.command(name="list")
@click.option(
    "--details",
    "-d",
    is_flag=True,
    help="Show detailed information for each plugin",
)
def list_plugins(details: bool) -> None:
    """List installed plugins.

    \b
    Examples:
      tripwire plugin list
      tripwire plugin list --details

    \b
    This command shows all plugins currently installed in
    ~/.tripwire/plugins/. Use --details to see version information
    and other metadata.
    """
    try:
        # Get installed plugins
        installer = PluginInstaller()
        installed = installer.list_installed()

        if not installed:
            console.print("[yellow]No plugins installed[/yellow]\n")
            console.print("[cyan]Tip:[/cyan] Install plugins with [bold]tripwire plugin install <name>[/bold]")
            console.print("[cyan]Search:[/cyan] Use [bold]tripwire plugin search[/bold] to find available plugins")
            return

        if details:
            # Fetch registry for version info
            registry_client = PluginRegistryClient()

            with console.status("Fetching plugin registry..."):
                registry = registry_client.fetch_registry(use_cache=True)

            # Display detailed table
            table = Table(
                title="Installed Plugins",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="green", width=20)
            table.add_column("Display Name", style="bold", width=25)
            table.add_column("Version", style="yellow", width=10)
            table.add_column("Type", width=12)
            table.add_column("Author", width=20)
            table.add_column("License", width=12)

            for plugin_id in sorted(installed):
                # Check if bundled plugin
                plugin_dir = installer.PLUGINS_DIR / plugin_id
                builtin_marker = plugin_dir / ".builtin"
                plugin_type = "(bundled)" if builtin_marker.exists() else "(installed)"

                plugin_entry = registry.get_plugin(plugin_id)
                if plugin_entry:
                    table.add_row(
                        plugin_entry.name,
                        plugin_entry.display_name,
                        plugin_entry.latest_version,
                        plugin_type,
                        plugin_entry.author,
                        plugin_entry.license,
                    )
                else:
                    # Plugin not in registry (custom plugin)
                    table.add_row(
                        plugin_id,
                        plugin_id,
                        "unknown",
                        "(custom)",
                        "unknown",
                        "unknown",
                    )

            console.print(table)
        else:
            # Simple list
            console.print("[bold]Installed Plugins:[/bold]\n")
            for plugin_id in sorted(installed):
                # Check if bundled plugin
                plugin_dir = installer.PLUGINS_DIR / plugin_id
                builtin_marker = plugin_dir / ".builtin"
                indicator = "[dim](bundled)[/dim]" if builtin_marker.exists() else ""
                console.print(f"  [green]✓[/green] {plugin_id} {indicator}")

            console.print(
                f"\n[cyan]Total:[/cyan] {len(installed)} plugin{'s' if len(installed) != 1 else ''} installed"
            )
            console.print("[cyan]Details:[/cyan] Use [bold]--details[/bold] for more information")

    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list plugins: {e}")
        raise click.Abort()
