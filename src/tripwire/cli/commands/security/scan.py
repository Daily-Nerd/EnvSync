"""Security scan command for TripWire CLI."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

from tripwire.branding import get_status_icon
from tripwire.cli.utils.console import console
from tripwire.cli.utils.helpers import should_skip_file_in_hook
from tripwire.secrets import SecretMatch

if TYPE_CHECKING:
    from tripwire.git_audit import SecretTimeline


@click.command(name="scan")
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with error if secrets found",
)
@click.option(
    "--depth",
    type=int,
    default=100,
    help="Number of git commits to scan",
)
def scan(strict: bool, depth: int) -> None:
    """Quick security check for secrets in .env and git history.

    Fast scan designed for pre-commit hooks and CI/CD pipelines.
    Detects potential secrets (API keys, tokens, passwords) to prevent
    accidental commits.

    For deep forensic analysis, use 'tripwire security audit' instead.
    """
    from rich.panel import Panel
    from rich.table import Table

    from tripwire.cli.utils.helpers import is_file_in_gitignore
    from tripwire.secrets import get_severity_color, scan_env_file, scan_git_history

    console.print("[yellow]Scanning for secrets...[/yellow]\n")

    # Scan current .env file
    env_path = Path(".env")
    env_findings: list[SecretMatch] = []
    env_is_ignored = False

    if env_path.exists():
        # In strict mode (pre-commit hooks), skip files in .gitignore
        if strict and should_skip_file_in_hook(env_path):
            console.print(f"[dim]Skipping {env_path} (in .gitignore - won't be committed)[/dim]\n")
        else:
            console.print("Scanning .env file...")
            env_findings = scan_env_file(env_path)
            env_is_ignored = is_file_in_gitignore(env_path)

            if env_findings:
                status = get_status_icon("info") if env_is_ignored else get_status_icon("invalid")
                console.print(f"{status} Found {len(env_findings)} potential secret(s) in .env\n")
            else:
                status = get_status_icon("valid")
                console.print(f"{status} No secrets found in .env\n")

    # Scan git history
    git_findings_list: list[dict[str, str]] = []
    if Path(".git").exists():
        console.print(f"Scanning last {depth} commits in git history...")
        git_findings_list = scan_git_history(Path.cwd(), depth=depth)

        if git_findings_list:
            console.print(f"[red]Found {len(git_findings_list)} potential secret(s) in git history[/red]\n")
        else:
            status = get_status_icon("valid")
            console.print(f"{status} No secrets found in git history\n")

    # Determine risk level based on where secrets are found
    has_git_history_secrets = len(git_findings_list) > 0
    has_env_secrets = len(env_findings) > 0

    # Calculate risk level
    if has_git_history_secrets:
        risk_level = "CRITICAL"
    elif has_env_secrets and not env_is_ignored:
        risk_level = "MEDIUM"
    elif has_env_secrets and env_is_ignored:
        risk_level = "LOW"
    else:
        risk_level = "NONE"

    # Display findings with context-aware messaging
    if risk_level != "NONE":
        # Prepare all findings for table
        all_findings: list[SecretMatch] = list(env_findings)

        # Add git findings to table
        if git_findings_list:
            from tripwire.secrets import SecretType

            seen: set[tuple[str, str]] = set()
            for git_finding in git_findings_list:
                key = (git_finding["variable"], git_finding["type"])
                if key not in seen:
                    seen.add(key)
                    # Create a proper SecretMatch object for git findings
                    try:
                        secret_type = SecretType(git_finding["type"])
                    except ValueError:
                        secret_type = SecretType.GENERIC_API_KEY

                    all_findings.append(
                        SecretMatch(
                            secret_type=secret_type,
                            variable_name=git_finding["variable"],
                            value="***",
                            line_number=0,
                            severity=git_finding["severity"],
                            recommendation=f"Found in commit {git_finding['commit']}. Rotate this secret immediately.",
                        )
                    )

        # Display findings table
        table = Table(title="Detected Secrets", show_header=True, header_style="bold red")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Recommendation")

        for finding in all_findings:
            severity_color = get_severity_color(finding.severity)
            table.add_row(
                finding.variable_name,
                finding.secret_type.value,
                f"[{severity_color}]{finding.severity.upper()}[/{severity_color}]",
                finding.recommendation[:80] + "..." if len(finding.recommendation) > 80 else finding.recommendation,
            )

        console.print(table)
        console.print()

        # Context-aware status and recommendations
        if risk_level == "CRITICAL":
            # Secrets in git history - CRITICAL
            console.print(
                Panel(
                    "[bold red]CRITICAL: Secrets found in version control![/bold red]\n\n"
                    f"Location: Git history ({len(git_findings_list)} commits)\n"
                    f".env status: {'In .gitignore ✓' if env_is_ignored else 'NOT in .gitignore ✗'}\n\n"
                    "[bold]⚠️  IMMEDIATE ACTION REQUIRED:[/bold]\n"
                    "  1. Rotate ALL detected secrets immediately\n"
                    "  2. Remove secrets from git history (use git filter-branch or BFG Repo-Cleaner)\n"
                    "  3. Add .env files to .gitignore if not already\n"
                    "  4. Never commit secrets to version control\n"
                    "  5. Use a secret manager for production (AWS Secrets Manager, Vault, etc.)",
                    border_style="red",
                    title="[!!] Security Alert",
                )
            )
        elif risk_level == "MEDIUM":
            # Secrets in committed files (not in .gitignore)
            console.print(
                Panel(
                    "[bold yellow]WARNING: Secrets in committed files![/bold yellow]\n\n"
                    "Location: .env (NOT in .gitignore ✗)\n"
                    "Git History: No secrets found ✓\n\n"
                    "[bold]Action Required:[/bold]\n"
                    "  1. Add .env to .gitignore immediately\n"
                    "  2. Remove .env from git index (git rm --cached .env)\n"
                    "  3. Consider rotating secrets if .env was previously committed\n"
                    "  4. Use .env.example for team templates (with placeholder values)\n"
                    "  5. Never commit real secrets to version control",
                    border_style="yellow",
                    title="[!] Configuration Warning",
                )
            )
        elif risk_level == "LOW":
            # Secrets only in .gitignore'd files - expected for local dev
            console.print(
                Panel(
                    "[bold cyan]INFO: Secrets found in local development files[/bold cyan]\n\n"
                    "Location: .env (in .gitignore ✓)\n"
                    "Git History: No secrets found ✓\n\n"
                    "[bold]Status: Expected for local development[/bold]\n"
                    "  ✓ .env is in .gitignore (won't be committed)\n"
                    "  ✓ No secrets found in version control\n"
                    "  ℹ These secrets are safe for local development\n\n"
                    "[bold]Best Practices:[/bold]\n"
                    "  1. Keep .env in .gitignore\n"
                    "  2. Use .env.example for team templates (with placeholder values)\n"
                    "  3. Consider secret manager for production (AWS Secrets Manager, Vault)\n"
                    "  4. Enable pre-commit hooks to prevent accidental commits",
                    border_style="cyan",
                    title="[i] Local Development",
                )
            )

        if strict and risk_level in ("CRITICAL", "MEDIUM"):
            sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} No secrets detected")
        console.print("Your environment files appear secure")


def _display_combined_timeline(
    results: list[tuple[SecretMatch, "SecretTimeline"]],
    console: Console,
) -> None:
    """Display combined visual timeline for multiple secrets.

    Args:
        results: List of (SecretMatch, SecretTimeline) tuples
        console: Rich console instance
    """
    from rich.panel import Panel
    from rich.tree import Tree

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


def _display_single_audit_result(
    secret_name: str,
    timeline: "SecretTimeline",
    console: Console,
) -> None:
    """Display audit results for a single secret.

    Args:
        secret_name: Name of the secret
        timeline: SecretTimeline object
        console: Rich console instance
    """
    from collections import defaultdict

    from rich.panel import Panel
    from rich.syntax import Syntax

    from tripwire.git_audit import generate_remediation_steps

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


__all__ = ["scan"]
