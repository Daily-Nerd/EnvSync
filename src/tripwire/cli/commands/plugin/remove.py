"""Plugin remove command for TripWire CLI."""

import click
from rich.console import Console

from tripwire.plugins import PluginInstaller

console = Console()


@click.command(name="remove")
@click.argument("plugin_id", type=str)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def remove(
    plugin_id: str,
    yes: bool,
) -> None:
    """Remove an installed plugin.

    \b
    Examples:
      tripwire plugin remove vault
      tripwire plugin remove aws-secrets --yes

    \b
    This command will:
      1. Check if the plugin is installed
      2. Prompt for confirmation (unless --yes is used)
      3. Remove the plugin directory

    Warning: This action cannot be undone. You'll need to reinstall
    the plugin if you want to use it again.
    """
    try:
        # Check if plugin is installed
        installer = PluginInstaller()

        if not installer.is_installed(plugin_id):
            console.print(f"[red]✗[/red] Plugin '{plugin_id}' is not installed\n")
            console.print("[cyan]Tip:[/cyan] Use [bold]tripwire plugin list[/bold] to see installed plugins")
            raise click.Abort()

        # Get plugin location
        plugin_dir = installer.PLUGINS_DIR / plugin_id

        # Confirm removal
        if not yes:
            console.print(f"\n[yellow]⚠[/yellow]  You are about to remove plugin '[bold]{plugin_id}[/bold]'")
            console.print(f"    Location: {plugin_dir}")
            console.print("\n    This action cannot be undone.\n")

            if not click.confirm("Do you want to continue?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Remove plugin
        with console.status(f"Removing {plugin_id}..."):
            installer.uninstall(plugin_id)

        console.print(f"\n[green]✓[/green] Plugin '{plugin_id}' removed successfully")
        console.print(f"\n[cyan]Reinstall:[/cyan] Use [bold]tripwire plugin install {plugin_id}[/bold] to reinstall")

    except RuntimeError as e:
        console.print(f"\n[red]✗[/red] Failed to remove plugin: {e}")
        raise click.Abort()
    except Exception as e:
        if not isinstance(e, click.Abort):
            console.print(f"\n[red]✗[/red] Unexpected error: {e}")
        raise click.Abort()
