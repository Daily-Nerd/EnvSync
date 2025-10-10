"""Audit result formatters for TripWire CLI.

Displays git history audit results in various visual formats.
"""

from collections import defaultdict

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree

from tripwire.branding import get_status_icon
from tripwire.git_audit import SecretTimeline, generate_remediation_steps
from tripwire.secrets import SecretMatch


def display_combined_timeline(
    results: list[tuple[SecretMatch, SecretTimeline]],
    console: Console,
) -> None:
    """Display combined visual timeline for multiple secrets.

    Args:
        results: List of (SecretMatch, SecretTimeline) tuples
        console: Rich console instance
    """
    console.print("\n[bold cyan][Report] Secret Leak Blast Radius[/bold cyan]")
    console.print("=" * 70)
    console.print()

    # Create visual tree
    tree = Tree("[*] [bold yellow]Repository Secret Exposure[/bold yellow]")

    for secret_match, timeline in results:
        if timeline.total_occurrences == 0:
            continue

        # Determine status symbol
        status_symbol = "[!]" if timeline.is_currently_in_git else "[~]"
        severity_symbol = "[!!]" if timeline.severity == "CRITICAL" else "[!]"

        secret_node = tree.add(
            f"{status_symbol} {severity_symbol} [yellow]{secret_match.variable_name}[/yellow] "
            f"([red]{timeline.total_occurrences} occurrence(s)[/red])"
        )

        # Add branches
        if timeline.branches_affected:
            branches_node = secret_node.add("[cyan]Branches affected:[/cyan]")
            for branch in timeline.branches_affected[:5]:
                # Note: Showing total commits across all branches since we don't track per-branch
                branches_node.add(f"+- {branch} ([yellow]{len(timeline.commits_affected)} total commits[/yellow])")

        # Add files
        if timeline.files_affected:
            files_node = secret_node.add("[cyan]Files affected:[/cyan]")
            for file_path in timeline.files_affected[:5]:
                files_node.add(f"+- [red]{file_path}[/red]")

    console.print(tree)
    console.print()

    # Summary statistics
    total_leaked = sum(1 for _, timeline in results if timeline.total_occurrences > 0)
    total_clean = len(results) - total_leaked
    total_commits = sum(len(timeline.commits_affected) for _, timeline in results)

    stats_panel = Panel(
        f"[bold red]Leaked:[/bold red] {total_leaked}\n"
        f"[bold green]Clean:[/bold green] {total_clean}\n"
        f"[bold yellow]Total commits affected:[/bold yellow] {total_commits}\n",
        title="[Chart] Summary",
        border_style="yellow",
    )

    console.print(stats_panel)
    console.print()


def display_single_audit_result(
    secret_name: str,
    timeline: SecretTimeline,
    console: Console,
) -> None:
    """Display audit results for a single secret.

    Args:
        secret_name: Name of the secret
        timeline: SecretTimeline object
        console: Rich console instance
    """
    # No leaks found
    if timeline.total_occurrences == 0:
        status = get_status_icon("valid")
        console.print(f"{status} No leaks found for {secret_name}")
        console.print("This secret does not appear in git history.")
        return

    # Display timeline header
    console.print(f"[bold cyan]Secret Leak Timeline for: {secret_name}[/bold cyan]")
    console.print("=" * 70)
    console.print()

    # Display timeline events
    if timeline.occurrences:
        console.print("[bold yellow]Timeline:[/bold yellow]\n")

        # Group occurrences by date
        from tripwire.git_audit import FileOccurrence

        by_date: dict[str, list[FileOccurrence]] = defaultdict(list)
        for occ in timeline.occurrences:
            date_str = occ.commit_date.strftime("%Y-%m-%d")
            by_date[date_str].append(occ)

        for date_str in sorted(by_date.keys()):
            occs = by_date[date_str]
            first_occ = occs[0]

            # Date header
            console.print(f"[bold][Date] {date_str}[/bold]")

            # Show commit info
            console.print(f"   Commit: [cyan]{first_occ.commit_hash[:8]}[/cyan] - {first_occ.commit_message[:60]}")
            console.print(f"   Author: [yellow]@{first_occ.author}[/yellow] <{first_occ.author_email}>")

            # Show files
            for occ in occs:
                console.print(f"   [File] [red]{occ.file_path}[/red]:{occ.line_number}")

            console.print()

        # Show current status
        if timeline.is_currently_in_git:
            status = get_status_icon("invalid")
            console.print(f"{status} [bold red]Still in git history (as of HEAD)[/bold red]")
        else:
            status = get_status_icon("valid")
            console.print(f"{status} Removed from current HEAD")

        console.print(f"   Affects [yellow]{len(timeline.commits_affected)}[/yellow] commit(s)")
        console.print(f"   Found in [yellow]{len(timeline.files_affected)}[/yellow] file(s)")

        if timeline.branches_affected:
            branches_str = ", ".join(timeline.branches_affected[:5])
            if len(timeline.branches_affected) > 5:
                branches_str += f", +{len(timeline.branches_affected) - 5} more"
            console.print(f"   Branches: [cyan]{branches_str}[/cyan]")

        console.print()

    # Security impact panel
    severity_color = {
        "CRITICAL": "red",
        "HIGH": "yellow",
        "MEDIUM": "blue",
        "LOW": "green",
    }.get(timeline.severity, "white")

    impact_lines = [
        f"[bold]Severity:[/bold] [{severity_color}]{timeline.severity}[/{severity_color}]",
        f"[bold]Exposure:[/bold] {'PUBLIC repository' if timeline.is_in_public_repo else 'Private repository'}",
        f"[bold]Duration:[/bold] {timeline.exposure_duration_days} days",
        f"[bold]Commits affected:[/bold] {len(timeline.commits_affected)}",
        f"[bold]Files affected:[/bold] {len(timeline.files_affected)}",
    ]

    if timeline.is_in_public_repo:
        impact_lines.append("")
        impact_lines.append("[bold red][!] CRITICAL: Found in PUBLIC repository![/bold red]")

    console.print(
        Panel(
            "\n".join(impact_lines),
            title="[!!] Security Impact",
            border_style="red" if timeline.severity == "CRITICAL" else "yellow",
        )
    )
    console.print()

    # Generate and display remediation steps
    steps = generate_remediation_steps(timeline, secret_name)

    console.print("[bold yellow][Fix] Remediation Steps:[/bold yellow]\n")

    for step in steps:
        urgency_color = {
            "CRITICAL": "red",
            "HIGH": "yellow",
            "MEDIUM": "blue",
            "LOW": "green",
        }.get(step.urgency, "white")

        console.print(f"[bold]{step.order}. {step.title}[/bold]")
        console.print(f"   Urgency: [{urgency_color}]{step.urgency}[/{urgency_color}]")
        console.print(f"   {step.description}")

        if step.command:
            console.print()
            # Syntax highlight the command
            # Convert list commands to string for display
            command_str = " ".join(step.command) if isinstance(step.command, list) else step.command
            syntax = Syntax(command_str, "bash", theme="monokai", line_numbers=False)
            console.print("   ", syntax)

        if step.warning:
            console.print(f"   [red][!] {step.warning}[/red]")

        console.print()

    # Final recommendations
    console.print("[bold cyan][Tip] Prevention Tips:[/bold cyan]")
    console.print("  - Always add .env files to .gitignore")
    console.print("  - Use environment variable scanning tools")
    console.print("  - Never commit secrets to version control")
    console.print("  - Use a secret manager for production")
    console.print("  - Enable pre-commit hooks to scan for secrets")
    console.print()


__all__ = ["display_combined_timeline", "display_single_audit_result"]
