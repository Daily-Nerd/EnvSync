"""Plugin search command for TripWire CLI."""

import click
from rich.console import Console
from rich.table import Table

from tripwire.plugins import PluginRegistryClient

console = Console()


@click.command(name="search")
@click.argument("query", type=str, required=False, default="")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Don't use cached registry (fetch from remote)",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=20,
    help="Maximum number of results to show (default: 20)",
)
def search(
    query: str,
    no_cache: bool,
    limit: int,
) -> None:
    """Search for plugins in the registry.

    \b
    Examples:
      tripwire plugin search vault
      tripwire plugin search aws
      tripwire plugin search           # List all plugins

    \b
    The search query matches against:
      - Plugin name
      - Display name
      - Description
      - Tags

    Results are ranked by relevance (name matches first, then description).
    """
    try:
        # Fetch registry
        registry_client = PluginRegistryClient()

        with console.status("Fetching plugin registry..."):
            registry = registry_client.fetch_registry(use_cache=not no_cache)

        # Search plugins
        results = registry.search(query)

        # Limit results
        results = results[:limit]

        if not results:
            console.print(f"[yellow]No plugins found matching '{query}'[/yellow]\n")
            console.print("[cyan]Tip:[/cyan] Try a different search term or check the spelling")
            return

        # Display results in table
        query_suffix = f' for "{query}"' if query else ""
        title = f"Plugin Search Results{query_suffix}"
        table = Table(
            title=title,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Name", style="green", width=20)
        table.add_column("Display Name", style="bold", width=25)
        table.add_column("Version", style="yellow", width=10)
        table.add_column("Description", width=50)
        table.add_column("Downloads", justify="right", style="blue", width=10)

        for plugin in results:
            table.add_row(
                plugin.name,
                plugin.display_name,
                plugin.latest_version,
                plugin.description[:47] + "..." if len(plugin.description) > 50 else plugin.description,
                str(plugin.total_downloads),
            )

        console.print(table)

        # Show install tip
        if results:
            console.print(f"\n[cyan]To install:[/cyan] tripwire plugin install <name>")
            console.print(f"[cyan]For details:[/cyan] Visit the plugin homepage")

    except RuntimeError as e:
        console.print(f"[red]✗[/red] Search failed: {e}")
        console.print("\n[yellow]Tip:[/yellow] Check your internet connection or try again later")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise click.Abort()
