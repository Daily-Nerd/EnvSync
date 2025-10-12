"""Plugin update command for TripWire CLI."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from tripwire.plugins import PluginInstaller, PluginRegistryClient

console = Console()


@click.command(name="update")
@click.argument("plugin_id", type=str)
@click.option(
    "--version",
    "-v",
    type=str,
    default=None,
    help="Specific version to update to (default: latest)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Don't use cached registry (fetch from remote)",
)
def update(
    plugin_id: str,
    version: str | None,
    no_cache: bool,
) -> None:
    """Update an installed plugin to a newer version.

    \b
    Examples:
      tripwire plugin update vault
      tripwire plugin update vault --version 0.3.0
      tripwire plugin update aws-secrets --no-cache

    \b
    This command will:
      1. Check if the plugin is installed
      2. Fetch available versions from registry
      3. Download and install the new version
      4. Replace the old version

    Note: The update process will overwrite the existing installation.
    """
    try:
        # Check if plugin is installed
        installer = PluginInstaller()

        if not installer.is_installed(plugin_id):
            console.print(f"[red]✗[/red] Plugin '{plugin_id}' is not installed\n")
            console.print(f"[cyan]Tip:[/cyan] Install it first with [bold]tripwire plugin install {plugin_id}[/bold]")
            raise click.Abort()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Fetch registry
            task = progress.add_task("Fetching plugin registry...", total=None)
            registry_client = PluginRegistryClient()
            registry = registry_client.fetch_registry(use_cache=not no_cache)
            progress.update(task, completed=True)

            # Get plugin entry
            plugin_entry = registry.get_plugin(plugin_id)
            if not plugin_entry:
                console.print(f"\n[red]✗[/red] Plugin '{plugin_id}' not found in registry\n")
                console.print(
                    "[yellow]Note:[/yellow] The plugin may have been removed from the registry " "or is a custom plugin"
                )
                raise click.Abort()

            # Get version to update to
            target_version = version or plugin_entry.latest_version
            version_info = plugin_entry.get_version(target_version)

            if not version_info:
                console.print(f"\n[red]✗[/red] Version '{target_version}' not found for plugin '{plugin_id}'\n")
                console.print(f"[yellow]Available versions:[/yellow] {', '.join(plugin_entry.versions.keys())}")
                raise click.Abort()

            # Display update info
            console.print(f"\n[bold]Updating {plugin_entry.display_name}[/bold]")
            console.print(f"  Target version: {target_version}")
            console.print(f"  Author: {plugin_entry.author}")
            console.print(f"  Description: {plugin_entry.description}\n")

            # Update plugin (install with force=True)
            task = progress.add_task(f"Updating {plugin_id}...", total=None)

            try:
                plugin_dir = installer.install(
                    plugin_id=plugin_id,
                    version=target_version,
                    force=True,  # Always force to overwrite existing
                )
                progress.update(task, completed=True)

                console.print(
                    f"\n[green]✓[/green] Plugin '{plugin_id}' updated successfully to version {target_version}!"
                )
                console.print(f"  Location: {plugin_dir}")
                console.print(
                    f"\n[yellow]Note:[/yellow] You may need to restart your application for changes to take effect"
                )

            except RuntimeError as e:
                progress.update(task, completed=True)
                console.print(f"\n[red]✗[/red] Update failed: {e}")
                raise click.Abort()

    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"\n[red]✗[/red] Update failed: {e}")
        raise click.Abort()
