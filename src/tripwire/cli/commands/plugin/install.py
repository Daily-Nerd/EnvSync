"""Plugin install command for TripWire CLI."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from tripwire.plugins import PluginInstaller, PluginRegistryClient

console = Console()


@click.command(name="install")
@click.argument("plugin_id", type=str)
@click.option(
    "--version",
    "-v",
    type=str,
    default=None,
    help="Specific version to install (default: latest)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinstall if already installed",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Don't use cached registry (fetch from remote)",
)
def install(
    plugin_id: str,
    version: str | None,
    force: bool,
    no_cache: bool,
) -> None:
    """Install a plugin from the registry.

    \b
    Examples:
      tripwire plugin install vault
      tripwire plugin install vault --version 0.2.0
      tripwire plugin install aws-secrets --force

    \b
    The plugin will be downloaded from the official registry, verified,
    and installed to ~/.tripwire/plugins/<plugin_id>.

    \b
    After installation, you can use the plugin with TripWire:
      from tripwire import TripWireV2
      from tripwire.plugins import PluginRegistry

      TripWireV2.discover_plugins()
      VaultSource = PluginRegistry.get_plugin("vault")
      env = TripWireV2(sources=[VaultSource(...)])
    """
    try:
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

            # Check if plugin exists
            plugin_entry = registry.get_plugin(plugin_id)
            if not plugin_entry:
                console.print(f"[red]✗[/red] Plugin '{plugin_id}' not found in registry\n")
                console.print("[yellow]Tip:[/yellow] Use [cyan]tripwire plugin search[/cyan] to find available plugins")
                raise click.Abort()

            # Get version info
            version_to_install = version or plugin_entry.latest_version
            version_info = plugin_entry.get_version(version_to_install)
            if not version_info:
                console.print(f"[red]✗[/red] Version '{version_to_install}' not found for plugin '{plugin_id}'\n")
                console.print(f"[yellow]Available versions:[/yellow] {', '.join(plugin_entry.versions.keys())}")
                raise click.Abort()

            # Display plugin info
            console.print(f"\n[bold]Installing {plugin_entry.display_name}[/bold]")
            console.print(f"  Version: {version_info.version}")
            console.print(f"  Author: {plugin_entry.author}")
            console.print(f"  License: {plugin_entry.license}")
            console.print(f"  Description: {plugin_entry.description}\n")

            # Install plugin
            installer = PluginInstaller(registry_client)
            task = progress.add_task(f"Installing {plugin_id}...", total=None)

            try:
                plugin_dir = installer.install(
                    plugin_id=plugin_id,
                    version=version_to_install,
                    force=force,
                )
                progress.update(task, completed=True)

                console.print(f"\n[green]✓[/green] Plugin '{plugin_id}' installed successfully!")
                console.print(f"  Location: {plugin_dir}")
                console.print(
                    f"\n[cyan]Next steps:[/cyan]\n"
                    f"  1. Import the plugin: TripWireV2.discover_plugins()\n"
                    f"  2. Use in code: See {plugin_entry.homepage} for usage examples"
                )

            except RuntimeError as e:
                progress.update(task, completed=True)
                if "already installed" in str(e):
                    console.print(f"\n[yellow]![/yellow] {e}")
                    console.print("[cyan]Tip:[/cyan] Use [bold]--force[/bold] to reinstall")
                else:
                    console.print(f"\n[red]✗[/red] {e}")
                raise click.Abort()

    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"\n[red]✗[/red] Installation failed: {e}")
        raise click.Abort()
