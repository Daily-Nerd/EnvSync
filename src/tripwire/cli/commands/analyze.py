"""Analyze commands for TripWire CLI.

Provides usage analysis, dead code detection, and dependency visualization for
environment variables across your Python codebase.

Commands:
    - analyze usage: Show comprehensive usage analysis
    - analyze deadcode: Find variables declared but never used
    - analyze dependencies: Visualize variable dependency graph
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.panel import Panel

from tripwire.analysis.dependency_graph import DependencyGraph
from tripwire.analysis.usage_tracker import UsageAnalyzer
from tripwire.cli.formatters.analyze import (
    render_deadcode_report,
    render_dependency_tree,
    render_usage_analysis,
)
from tripwire.cli.utils.console import console


@click.group()
def analyze() -> None:
    """Analyze environment variable usage and dependencies.

    Commands for discovering dead environment variables, visualizing usage
    patterns, and generating dependency graphs.

    Common Workflows:

      Find Dead Variables:
        tripwire analyze deadcode           # Show unused variables
        tripwire analyze deadcode --strict  # CI/CD mode (exit 1 if found)

      Usage Analysis:
        tripwire analyze usage              # Full analysis
        tripwire analyze usage --show-unused # Only unused vars

      Export Visualizations:
        tripwire analyze dependencies --format mermaid --export deps.md
        tripwire analyze dependencies --format dot --export graph.dot
    """
    pass


@analyze.command()
@click.option(
    "--show-used",
    is_flag=True,
    help="Show only used variables",
)
@click.option(
    "--show-unused",
    is_flag=True,
    help="Show only unused variables",
)
@click.option(
    "--format",
    type=click.Choice(["terminal", "json"]),
    default="terminal",
    help="Output format",
)
@click.option(
    "--min-usage",
    type=int,
    help="Only show vars used >= N times",
)
@click.option(
    "--export",
    type=click.Path(),
    help="Export to file",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit 1 on first dead variable found (CI/CD mode)",
)
def usage(
    show_used: bool,
    show_unused: bool,
    format: str,
    min_usage: Optional[int],
    export: Optional[str],
    strict: bool,
) -> None:
    """Analyze environment variable usage across codebase.

    Scans Python files to track where environment variables are declared
    and used, identifying both active variables and dead code.

    Exit Codes:
        0 - No dead variables found (success)
        1 - Dead variables found (when using --strict)

    Strict Mode:
        When --strict is enabled, the command fails fast on the FIRST dead
        variable found. This is ideal for CI/CD pipelines where you want to
        enforce zero dead code policy and fail builds immediately.

    Examples:
        tripwire analyze usage                  # Show full analysis
        tripwire analyze usage --show-unused    # Only show dead vars
        tripwire analyze usage --format json --export usage.json
        tripwire analyze usage --strict         # Fail fast on first dead var
        tripwire analyze usage --min-usage 5    # Only heavily used vars
    """
    project_root = Path.cwd()

    # Run analysis
    try:
        console.print("[dim]Analyzing codebase...[/dim]")
        analyzer = UsageAnalyzer(project_root)
        result = analyzer.analyze()
    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        sys.exit(1)

    # Strict mode - fail fast on first dead variable
    if strict and len(result.dead_variables) > 0:
        # Get first dead variable (sorted alphabetically for consistency)
        first_dead = sorted(result.dead_variables)[0]
        decl = result.declarations[first_dead]

        console.print()
        console.print(
            Panel.fit(
                f"[bold red]FAILED: Dead variable detected[/bold red]",
                border_style="red",
            )
        )
        console.print()

        # Show detailed info about the first dead variable
        from rich.text import Text

        error_text = Text()
        error_text.append("Variable: ", style="bold")
        error_text.append(f"{first_dead}\n", style="yellow bold")
        error_text.append("Env Var: ", style="bold")
        error_text.append(f"{decl.env_var}\n", style="dim")
        error_text.append("Location: ", style="bold")
        error_text.append(f"{decl.file_path}:{decl.line_number}\n\n", style="cyan")

        error_text.append("Remediation:\n", style="bold green")
        error_text.append(f"  1. Delete line {decl.line_number} from {decl.file_path.name}\n")
        error_text.append(f"  2. Remove {decl.env_var} from .env files\n")
        error_text.append("  3. Run: tripwire schema from-code --exclude-unused\n\n")

        if len(result.dead_variables) > 1:
            error_text.append(
                f"Note: {len(result.dead_variables) - 1} additional dead variable(s) found. "
                f"Run without --strict to see all.\n",
                style="dim yellow",
            )

        console.print(Panel(error_text, border_style="red", title="Dead Code Detected"))
        console.print()
        console.print("[red bold]Build failed due to dead code policy violation[/red bold]")
        console.print()
        sys.exit(1)

    # Filter by minimum usage if requested
    if min_usage is not None:
        filtered_usages = {var: usages for var, usages in result.usages.items() if len(usages) >= min_usage}
        result.usages = filtered_usages

    # Output based on format
    if format == "terminal":
        # Filter display based on flags
        if show_used and not show_unused:
            # Only show used variables
            result.declarations = {
                name: decl for name, decl in result.declarations.items() if name in result.used_variables
            }
        elif show_unused and not show_used:
            # Only show unused variables
            result.declarations = {
                name: decl for name, decl in result.declarations.items() if name in result.dead_variables
            }

        render_usage_analysis(result)

    elif format == "json":
        graph = DependencyGraph(result)
        output_data = graph.export_json()

        if export:
            Path(export).write_text(json.dumps(output_data, indent=2))
            console.print(f"[green]Exported to {export}[/green]")
        else:
            print(json.dumps(output_data, indent=2))


@analyze.command()
@click.option(
    "--strict",
    is_flag=True,
    help="Exit 1 on first dead variable found (CI/CD mode)",
)
@click.option(
    "--export",
    type=click.Path(),
    help="Export to JSON file",
)
def deadcode(strict: bool, export: Optional[str]) -> None:
    """Find environment variables that are declared but never used.

    Performs focused analysis to identify dead environment variables -
    those declared via env.require() or env.optional() but never
    referenced anywhere in your codebase.

    Exit Codes:
        0 - No dead variables found (success)
        1 - Dead variables found (when using --strict)

    Strict Mode:
        When --strict is enabled, the command fails fast on the FIRST dead
        variable found. This is ideal for CI/CD pipelines where you want to
        enforce zero dead code policy and fail builds immediately.

    Examples:
        tripwire analyze deadcode                # Show all dead variables
        tripwire analyze deadcode --strict       # Fail fast on first dead var
        tripwire analyze deadcode --export dead-vars.json
    """
    project_root = Path.cwd()

    # Run analysis
    try:
        console.print("[dim]Analyzing codebase...[/dim]")
        analyzer = UsageAnalyzer(project_root)
        result = analyzer.analyze()
    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        sys.exit(1)

    # Strict mode - fail fast on first dead variable
    if strict and len(result.dead_variables) > 0:
        # Get first dead variable (sorted alphabetically for consistency)
        first_dead = sorted(result.dead_variables)[0]
        decl = result.declarations[first_dead]

        console.print()
        console.print(
            Panel.fit(
                f"[bold red]FAILED: Dead variable detected[/bold red]",
                border_style="red",
            )
        )
        console.print()

        # Show detailed info about the first dead variable
        from rich.text import Text

        error_text = Text()
        error_text.append("Variable: ", style="bold")
        error_text.append(f"{first_dead}\n", style="yellow bold")
        error_text.append("Env Var: ", style="bold")
        error_text.append(f"{decl.env_var}\n", style="dim")
        error_text.append("Location: ", style="bold")
        error_text.append(f"{decl.file_path}:{decl.line_number}\n\n", style="cyan")

        error_text.append("Remediation:\n", style="bold green")
        error_text.append(f"  1. Delete line {decl.line_number} from {decl.file_path.name}\n")
        error_text.append(f"  2. Remove {decl.env_var} from .env files\n")
        error_text.append("  3. Run: tripwire schema from-code --exclude-unused\n\n")

        if len(result.dead_variables) > 1:
            error_text.append(
                f"Note: {len(result.dead_variables) - 1} additional dead variable(s) found. "
                f"Run without --strict to see all.\n",
                style="dim yellow",
            )

        console.print(Panel(error_text, border_style="red", title="Dead Code Detected"))
        console.print()
        console.print("[red bold]Build failed due to dead code policy violation[/red bold]")
        console.print()
        sys.exit(1)

    # Normal mode - render full report
    render_deadcode_report(result)

    # Export if requested
    if export:
        dead_vars_data = [
            {
                "variable": var,
                "env_var": result.declarations[var].env_var,
                "file": str(result.declarations[var].file_path),
                "line": result.declarations[var].line_number,
                "is_required": result.declarations[var].is_required,
                "type": result.declarations[var].type_annotation,
            }
            for var in result.dead_variables
        ]
        Path(export).write_text(json.dumps(dead_vars_data, indent=2))
        console.print(f"\n[green]Exported to {export}[/green]")


@analyze.command()
@click.option(
    "--var",
    help="Show dependencies for specific variable",
)
@click.option(
    "--format",
    type=click.Choice(["terminal", "json", "mermaid", "dot"]),
    default="terminal",
    help="Output format",
)
@click.option(
    "--export",
    type=click.Path(),
    help="Export to file",
)
@click.option(
    "--top",
    type=int,
    help="Show only top N most-used variables",
)
@click.option(
    "--min-uses",
    type=int,
    help="Only show variables with >= N usages",
)
@click.option(
    "--dead-only",
    is_flag=True,
    help="Show only unused (dead) variables",
)
@click.option(
    "--used-only",
    is_flag=True,
    help="Show only used variables (exclude dead)",
)
def dependencies(
    var: Optional[str],
    format: str,
    export: Optional[str],
    top: Optional[int],
    min_uses: Optional[int],
    dead_only: bool,
    used_only: bool,
) -> None:
    """Visualize environment variable dependencies.

    Shows where variables are used across your codebase, with support
    for multiple output formats including Mermaid (GitHub markdown) and
    Graphviz DOT for high-quality diagrams.

    Examples:
        tripwire analyze dependencies                   # Terminal view
        tripwire analyze dependencies --var DATABASE_URL
        tripwire analyze dependencies --format mermaid --export deps.md
        tripwire analyze dependencies --format dot --export graph.dot
        tripwire analyze dependencies --top 10 --format mermaid
        tripwire analyze dependencies --min-uses 5 --format dot
        tripwire analyze dependencies --dead-only --export dead-vars.json

    Render DOT files:
        dot -Tpng graph.dot -o graph.png
        dot -Tsvg graph.dot -o graph.svg
    """
    project_root = Path.cwd()

    # Validate conflicting options
    if dead_only and used_only:
        console.print("[red]Error: Cannot use --dead-only and --used-only together[/red]")
        sys.exit(1)

    if top and min_uses:
        console.print("[red]Error: Cannot use --top and --min-uses together[/red]")
        sys.exit(1)

    # Run analysis
    try:
        console.print("[dim]Analyzing codebase...[/dim]")
        analyzer = UsageAnalyzer(project_root)
        result = analyzer.analyze()
    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        sys.exit(1)

    # Build dependency graph
    graph = DependencyGraph(result)

    # Apply filters if specified
    original_count = len(graph.nodes)

    if top:
        graph = graph.filter_by_top_n(top)
        console.print(f"[dim]Filtered to top {top} variables (from {original_count} total)[/dim]")
    elif min_uses:
        graph = graph.filter_by_min_usage(min_uses)
        filtered_count = len(graph.nodes)
        console.print(
            f"[dim]Filtered to {filtered_count} variables with >={min_uses} uses "
            f"(from {original_count} total)[/dim]"
        )
    elif dead_only:
        graph = graph.filter_dead_only()
        console.print(f"[dim]Showing {len(graph.nodes)} dead variables (from {original_count} total)[/dim]")
    elif used_only:
        graph = graph.filter_used_only()
        console.print(f"[dim]Showing {len(graph.nodes)} used variables (from {original_count} total)[/dim]")

    # Filter by specific variable if requested
    if var:
        if var not in graph.nodes:
            console.print(f"[red]Error: Variable '{var}' not found in codebase[/red]")
            console.print("\n[dim]Available variables:[/dim]")
            for v in sorted(graph.nodes.keys())[:10]:
                console.print(f"  - {v}")
            if len(graph.nodes) > 10:
                console.print(f"  ... and {len(graph.nodes) - 10} more")
            sys.exit(1)

        # Show only this variable
        node = graph.nodes[var]
        console.print()
        console.print(
            Panel.fit(
                f"[bold cyan]Dependencies for {var}[/bold cyan]",
                border_style="cyan",
            )
        )
        console.print()

        # Show declaration
        console.print(f"[bold]Declaration:[/bold]")
        console.print(f"  File: {node.declaration.file_path}:{node.declaration.line_number}")
        console.print(f"  Type: {node.declaration.type_annotation or 'unknown'}")
        console.print(f"  Required: {'Yes' if node.declaration.is_required else 'No'}")
        console.print()

        # Show usages
        if node.usages:
            console.print(f"[bold]Usages ({len(node.usages)}):[/bold]")
            # Group by file
            by_file: Dict[str, List[int]] = {}
            for usage in node.usages:
                file_name = str(usage.file_path)
                if file_name not in by_file:
                    by_file[file_name] = []
                by_file[file_name].append(usage.line_number)

            for file_path, lines in sorted(by_file.items()):
                console.print(f"  📄 {file_path}")
                line_list = sorted(lines)
                if len(line_list) <= 5:
                    console.print(f"     Lines: {', '.join(map(str, line_list))}")
                else:
                    console.print(f"     Lines: {', '.join(map(str, line_list[:5]))} ... +{len(line_list)-5} more")
        else:
            console.print("[yellow]No usages found (dead code)[/yellow]")

        console.print()
        return

    # Warn about large graphs before export
    if format in ("mermaid", "dot") and len(graph.nodes) > 20 and not export:
        console.print()
        console.print(
            Panel(
                f"[bold yellow]Large Graph Warning[/bold yellow]\n\n"
                f"This graph contains [bold]{len(graph.nodes)} nodes[/bold], which may be "
                f"difficult to visualize.\n\n"
                f"[bold]Suggestions:[/bold]\n"
                f"  • Use [cyan]--top 10[/cyan] to show most-used variables only\n"
                f"  • Use [cyan]--min-uses 5[/cyan] to filter low-usage vars\n"
                f"  • Use [cyan]--used-only[/cyan] to exclude dead variables\n"
                f"  • Use [cyan]--dead-only[/cyan] to analyze unused vars separately\n\n"
                f"[dim]Proceeding with full graph export...[/dim]",
                border_style="yellow",
                title="Visualization Tip",
            )
        )
        console.print()

    # Output based on format
    if format == "terminal":
        render_dependency_tree(graph)

    elif format == "mermaid":
        output = "```mermaid\n" + graph.export_mermaid() + "\n```"

        if export:
            Path(export).write_text(output)
            console.print(f"[green]Exported Mermaid diagram to {export}[/green]")
            console.print("[dim]Tip: Add this to your README.md - GitHub renders it automatically[/dim]")
        else:
            print(output)

    elif format == "dot":
        output = graph.export_dot()

        if export:
            Path(export).write_text(output)
            console.print(f"[green]Exported DOT graph to {export}[/green]")
            console.print(f"[dim]Render with: dot -Tpng {export} -o graph.png[/dim]")
        else:
            print(output)

    elif format == "json":
        output_data = graph.export_json()

        if export:
            Path(export).write_text(json.dumps(output_data, indent=2))
            console.print(f"[green]Exported to {export}[/green]")
        else:
            print(json.dumps(output_data, indent=2))


__all__ = ["analyze"]
