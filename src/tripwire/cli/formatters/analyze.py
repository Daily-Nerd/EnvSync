"""Rich terminal output formatters for usage analysis commands.

Provides beautiful, user-friendly rendering of usage analysis results using
the rich library for terminal formatting.
"""

from pathlib import Path
from typing import Dict, List, Optional

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from tripwire.analysis.dependency_graph import DependencyGraph
from tripwire.analysis.models import UsageAnalysisResult
from tripwire.cli.utils.console import console


def render_usage_analysis(result: UsageAnalysisResult) -> None:
    """Render beautiful usage analysis output with rich formatting.

    Displays:
    - Summary statistics panel (total, used, dead, coverage)
    - Dead variables table (if any) with remediation steps
    - Active variables table with usage counts
    - Dependency tree for top variables

    Args:
        result: Complete usage analysis result
    """
    # Header
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]TripWire Usage Analysis[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    # Summary statistics
    total_vars = result.total_variables
    used_vars = len(result.used_variables)
    dead_vars = len(result.dead_variables)

    if total_vars == 0:
        console.print("[yellow]No environment variables found in codebase[/yellow]")
        console.print("\nMake sure you're using env.require() or env.optional() in your code.")
        return

    summary_table = Table(show_header=False, box=box.SIMPLE)
    summary_table.add_column(style="cyan")
    summary_table.add_column(style="bold")

    summary_table.add_row("Total Variables", str(total_vars))
    summary_table.add_row("Used Variables", f"[green]{used_vars}[/green]")
    summary_table.add_row("Dead Variables", f"[red]{dead_vars}[/red]")
    summary_table.add_row("Coverage", f"{result.coverage_percentage:.1f}%")

    console.print(Panel(summary_table, title="Summary", border_style="blue"))
    console.print()

    # Dead variables section
    if dead_vars > 0:
        console.print("[bold red]⚠️  Dead Variables (Declared but Never Used)[/bold red]")
        console.print()

        dead_table = Table(show_header=True, box=box.ROUNDED)
        dead_table.add_column("Variable", style="yellow", width=30)
        dead_table.add_column("Env Var", style="dim", width=30)
        dead_table.add_column("Location", style="cyan")
        dead_table.add_column("Type", style="magenta")

        for var_name in sorted(result.dead_variables):
            decl = result.declarations[var_name]
            location = f"{decl.file_path.name}:{decl.line_number}"
            var_type = decl.type_annotation or "unknown"

            dead_table.add_row(var_name, decl.env_var, location, var_type)

        console.print(dead_table)
        console.print()

        # Remediation suggestions
        console.print(
            Panel(
                "[bold]💡 Suggested Actions:[/bold]\n\n"
                "1. Review each variable to confirm it's truly unused\n"
                "2. Remove declarations from Python files\n"
                "3. Remove from .env and .env.example\n"
                "4. Update schema: [cyan]tripwire schema from-code --exclude-unused[/cyan]\n"
                "5. Commit changes and verify tests pass",
                title="Remediation Steps",
                border_style="yellow",
            )
        )
        console.print()

    # Used variables section
    if used_vars > 0:
        console.print("[bold green]✅ Active Variables (Declared and Used)[/bold green]")
        console.print()

        used_table = Table(show_header=True, box=box.ROUNDED)
        used_table.add_column("Variable", style="green", width=30)
        used_table.add_column("Usage Count", justify="right", style="bold")
        used_table.add_column("Locations", style="cyan")
        used_table.add_column("First Use", style="dim")

        # Sort by usage count (descending)
        sorted_vars = sorted(
            result.used_variables,
            key=lambda v: len(result.usages.get(v, [])),
            reverse=True,
        )

        for var_name in sorted_vars:
            usages = result.usages.get(var_name, [])
            usage_count = len(usages)

            # Get unique file locations
            files = set(u.file_path.name for u in usages)
            file_count = len(files)
            locations = f"{file_count} file{'s' if file_count != 1 else ''}"

            # First usage
            first_use = usages[0] if usages else None
            first_loc = f"{first_use.file_path.name}:{first_use.line_number}" if first_use else "N/A"

            # Color code by usage frequency
            if usage_count >= 10:
                count_str = f"[bold green]{usage_count}[/bold green]"
            elif usage_count >= 5:
                count_str = f"[green]{usage_count}[/green]"
            else:
                count_str = f"[yellow]{usage_count}[/yellow]"

            used_table.add_row(var_name, count_str, locations, first_loc)

        console.print(used_table)
        console.print()

    # Dependency tree for top variables
    if used_vars > 0:
        console.print("[bold cyan]📊 Top Variable Usage[/bold cyan]")
        console.print()

        tree = Tree("🌳 Environment Variables")

        # Show top 5 most-used variables with their usage locations
        top_vars = sorted(
            result.used_variables,
            key=lambda v: len(result.usages.get(v, [])),
            reverse=True,
        )[:5]

        for var_name in top_vars:
            usages = result.usages.get(var_name, [])
            var_node = tree.add(f"[bold green]{var_name}[/bold green] ({len(usages)} uses)")

            # Group by file
            by_file: Dict[str, List[int]] = {}
            for usage in usages:
                file_name = usage.file_path.name
                if file_name not in by_file:
                    by_file[file_name] = []
                by_file[file_name].append(usage.line_number)

            for file_name, lines in sorted(by_file.items()):
                file_node = var_node.add(f"📄 {file_name}")
                line_summary = f"Lines: {', '.join(map(str, sorted(lines)[:5]))}"
                if len(lines) > 5:
                    line_summary += f" ... +{len(lines)-5} more"
                file_node.add(f"[dim]{line_summary}[/dim]")

        console.print(tree)
        console.print()


def render_deadcode_report(result: UsageAnalysisResult) -> None:
    """Render focused output for dead code detection.

    Displays either success message if no dead variables found, or
    detailed removal instructions for each dead variable.

    Args:
        result: Complete usage analysis result
    """
    dead_vars = result.dead_variables

    if not dead_vars:
        console.print()
        console.print(
            Panel(
                "[bold green]✅ No dead variables found![/bold green]\n\n"
                "All declared environment variables are being used.",
                border_style="green",
            )
        )
        console.print()
        return

    # Show dead variables with removal instructions
    console.print()
    console.print(
        Panel.fit(
            f"[bold red]⚠️  Found {len(dead_vars)} Dead Variable(s)[/bold red]",
            border_style="red",
        )
    )
    console.print()

    for var_name in sorted(dead_vars):
        decl = result.declarations[var_name]

        # Create removal panel for each variable
        removal_text = Text()
        removal_text.append("Variable: ", style="bold")
        removal_text.append(f"{var_name}\n", style="yellow bold")
        removal_text.append("Env Var: ", style="bold")
        removal_text.append(f"{decl.env_var}\n", style="dim")
        removal_text.append("Location: ", style="bold")
        removal_text.append(f"{decl.file_path}:{decl.line_number}\n\n", style="cyan")

        removal_text.append("🔧 To remove:\n", style="bold green")
        removal_text.append(f"  1. Delete line {decl.line_number} from {decl.file_path.name}\n")
        removal_text.append(f"  2. Remove {decl.env_var} from .env files\n")
        removal_text.append("  3. Run: tripwire schema from-code --exclude-unused\n")

        console.print(Panel(removal_text, border_style="red"))
        console.print()


def render_dependency_tree(graph: DependencyGraph, var_name: Optional[str] = None) -> None:
    """Render dependency tree showing variable usage.

    Shows:
    - Variable usage counts
    - Files where each variable is used
    - Line numbers grouped by file

    Args:
        graph: Dependency graph with all nodes
        var_name: Optional specific variable to show (None = show all)
    """
    console.print("[bold cyan]📊 Variable Dependencies[/bold cyan]")
    console.print()

    if var_name:
        # Show single variable
        node = graph.get_node(var_name)
        if not node:
            console.print(f"[red]Variable '{var_name}' not found[/red]")
            return

        tree = Tree(f"🌳 {var_name}")

        if node.is_dead:
            tree.add("[red]DEAD CODE - No usages[/red]")
        else:
            # Group by file
            by_file: Dict[str, List[int]] = {}
            for usage in node.usages:
                file_name = usage.file_path.name
                if file_name not in by_file:
                    by_file[file_name] = []
                by_file[file_name].append(usage.line_number)

            for file_name, lines in sorted(by_file.items()):
                file_node = tree.add(f"📄 {file_name}")
                line_summary = f"Lines: {', '.join(map(str, sorted(lines)[:5]))}"
                if len(lines) > 5:
                    line_summary += f" ... +{len(lines)-5} more"
                file_node.add(f"[dim]{line_summary}[/dim]")

    else:
        # Show top variables
        tree = Tree("🌳 Environment Variables")

        # Get top 10 most-used variables
        top_nodes = graph.get_top_used(limit=10)

        for node in top_nodes:
            if node.is_dead:
                var_node = tree.add(f"[red]{node.variable_name}[/red] (DEAD CODE)")
                continue

            var_node = tree.add(f"[bold green]{node.variable_name}[/bold green] ({node.usage_count} uses)")

            # Group by file
            file_groups: Dict[str, List[int]] = {}
            for usage in node.usages:
                file_name = usage.file_path.name
                if file_name not in file_groups:
                    file_groups[file_name] = []
                file_groups[file_name].append(usage.line_number)

            for file_name, lines in sorted(file_groups.items()):
                file_node = var_node.add(f"📄 {file_name}")
                line_summary = f"Lines: {', '.join(map(str, sorted(lines)[:5]))}"
                if len(lines) > 5:
                    line_summary += f" ... +{len(lines)-5} more"
                file_node.add(f"[dim]{line_summary}[/dim]")

        # Show dead variables if any
        dead_nodes = graph.get_dead_nodes()
        if dead_nodes:
            console.print(tree)
            console.print()
            console.print(
                f"[yellow]⚠️  {len(dead_nodes)} dead variable(s) (use 'tripwire analyze deadcode' for details)[/yellow]"
            )
            console.print()
            return

    console.print(tree)
    console.print()


__all__ = [
    "render_usage_analysis",
    "render_deadcode_report",
    "render_dependency_tree",
]
