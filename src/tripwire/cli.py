"""Command-line interface for TripWire.

This module provides CLI commands for environment variable management,
including generation, validation, and team synchronization features.
"""

import fnmatch
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click
from rich.console import Console

from tripwire.branding import LOGO_BANNER, LOGO_SIMPLE, get_status_icon, print_status
from tripwire.config.models import ConfigValue

# On Windows, force UTF-8 encoding for Rich console to support Unicode characters
# Use legacy_windows=False to avoid the cp1252 encoding issue
console = Console(legacy_windows=False)

# Project template definitions (module-level constant)
# Templates use {secret_section} placeholder for dynamic secret injection
PROJECT_TEMPLATES = {
    "web": {
        "base": """# Web Application Configuration
# Database connection
DATABASE_URL=postgresql://localhost:5432/mydb

# Security
{secret_section}
DEBUG=false

# Server configuration
PORT=8000
ALLOWED_HOSTS=localhost,127.0.0.1
""",
        "secret_comment": """# IMPORTANT: This is a randomly generated key for development.
# Generate a new random key for production!""",
        "placeholder_comment": """# IMPORTANT: Generate a secure random key for production!
# Never commit real secrets to version control.""",
    },
    "cli": {
        "base": """# CLI Tool Configuration
# API access
API_KEY=your-api-key-here

# Logging
DEBUG=false
LOG_LEVEL=INFO
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
    "data": {
        "base": """# Data Pipeline Configuration
# Database
DATABASE_URL=postgresql://localhost:5432/mydb

# Cloud storage
S3_BUCKET=my-data-bucket
AWS_REGION=us-east-1

# Processing
DEBUG=false
MAX_WORKERS=4
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
    "other": {
        "base": """# Application Configuration
# Add your environment variables here

# Example: API key
# API_KEY=your-api-key-here

# Example: Debug mode
DEBUG=false
""",
        "secret_comment": "",
        "placeholder_comment": "",
    },
}


def print_help_with_banner(ctx, param, value):
    """Show banner before help text."""
    if value and not ctx.resilient_parsing:
        console.print(f"[cyan]{LOGO_BANNER}[/cyan]")
        console.print(ctx.get_help())
        ctx.exit()


@click.group()
@click.option(
    "--help",
    "-h",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=print_help_with_banner,
    help="Show this message and exit.",
)
@click.version_option(version="0.4.0", prog_name="tripwire", message=f"{LOGO_SIMPLE}\nVersion: %(version)s")
def main() -> None:
    """TripWire - Catch config errors before they explode.

    Validate environment variables at import time with type safety,
    format validation, secret detection, and git audit capabilities.
    """
    pass


@main.command()
@click.option(
    "--project-type",
    type=click.Choice(["web", "cli", "data", "other"]),
    default="other",
    help="Type of project (affects starter variables)",
)
def init(project_type: str) -> None:
    """Initialize TripWire in your project.

    Creates .env, .env.example, and updates .gitignore with project-specific
    starter variables based on your project type.
    """
    console.print(f"[cyan]{LOGO_BANNER}[/cyan]")
    console.print("[bold cyan]Initializing TripWire in your project...[/bold cyan]\n")

    # Generate a secure random key for SECRET_KEY in .env only
    random_secret_key = secrets.token_urlsafe(32)

    # Helper function to generate templates with secret injection
    def get_template(project_type: str, inject_secret: bool = False) -> str:
        """Generate environment template with optional secret injection.

        Args:
            project_type: Type of project (web, cli, data, other)
            inject_secret: If True, use real random secret; if False, use placeholder

        Returns:
            Formatted template string with secrets injected appropriately
        """
        # Get template data from module-level constant
        template_data = PROJECT_TEMPLATES.get(project_type, PROJECT_TEMPLATES["other"])

        # Build secret section based on injection mode
        if inject_secret:
            # Real random secret for .env file
            comment = template_data["secret_comment"]
            secret_line = f"SECRET_KEY={random_secret_key}" if comment else ""
            secret_section = f"{comment}\n{secret_line}" if comment else secret_line
        else:
            # Placeholder for .env.example file
            comment = template_data["placeholder_comment"]
            secret_line = "SECRET_KEY=CHANGE_ME_TO_RANDOM_SECRET_KEY" if comment else ""
            secret_section = f"{comment}\n{secret_line}" if comment else secret_line

        return template_data["base"].format(secret_section=secret_section)

    # Create .env file (with real random secrets)
    env_path = Path(".env")
    if env_path.exists():
        console.print("[yellow][!] .env already exists, skipping...[/yellow]")
    else:
        env_path.write_text(get_template(project_type, inject_secret=True))
        console.print("[green][OK] Created .env[/green]")

    # Create .env.example (with placeholder secrets only)
    example_path = Path(".env.example")
    if example_path.exists():
        console.print("[yellow][!] .env.example already exists, skipping...[/yellow]")
    else:
        # Use placeholder template for .env.example to avoid committing real secrets
        # Real random secrets only go in .env (which is gitignored)
        example_content = get_template(project_type, inject_secret=False)

        # Add header comment to .env.example
        example_with_header = f"""# TripWire Environment Variables Template
# Copy this file to .env and fill in your actual values:
#   cp .env.example .env
#
# Never commit .env to version control!

{example_content}"""
        example_path.write_text(example_with_header)
        console.print("[green][OK] Created .env.example[/green]")

    # Update .gitignore
    gitignore_path = Path(".gitignore")
    gitignore_content = gitignore_path.read_text() if gitignore_path.exists() else ""

    # Check if .env is already protected by any pattern
    # Use fnmatch to properly handle gitignore glob patterns:
    #   .env*    matches .env (and .envrc, .environment, etc.)
    #   .env.*   matches .env.local, .env.prod (but NOT .env)
    #   .env     matches .env exactly
    gitignore_lines = [
        line.strip() for line in gitignore_content.splitlines() if line.strip() and not line.strip().startswith("#")
    ]
    has_env_entry = any(fnmatch.fnmatch(".env", pattern) for pattern in gitignore_lines)

    if not has_env_entry:
        with gitignore_path.open("a") as f:
            # Add proper spacing based on whether file exists and has content
            if gitignore_content:
                if not gitignore_content.endswith("\n"):
                    f.write("\n")
                f.write("\n# Environment variables (TripWire)\n")
            else:
                # New file - no leading newline
                f.write("# Environment variables (TripWire)\n")

            f.write(".env\n")
            f.write(".env.local\n")
        console.print("[green][OK] Updated .gitignore[/green]")
    else:
        console.print("[yellow][!] .gitignore already contains .env entries[/yellow]")

    # Success message
    console.print("\n[bold green]Setup complete![/bold green]\n")
    console.print("Next steps:")
    console.print("  1. Edit .env with your configuration values")
    console.print("  2. Import in your code: [cyan]from tripwire import env[/cyan]")
    console.print("  3. Use variables: [cyan]API_KEY = env.require('API_KEY')[/cyan]")
    console.print("\nFor help: [cyan]tripwire --help[/cyan]\n")


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".env.example",
    help="Output file path",
)
@click.option(
    "--check",
    is_flag=True,
    help="Check if .env.example is up to date (CI mode)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing file",
)
def generate(output: str, check: bool, force: bool) -> None:
    """Generate .env.example file from code.

    Scans your Python code for env.require() and env.optional() calls
    and generates a .env.example file documenting all environment variables.
    """
    from tripwire.scanner import (
        deduplicate_variables,
        format_var_for_env_example,
        scan_directory,
    )

    console.print("[yellow]Scanning Python files for environment variables...[/yellow]")

    # Scan current directory for env usage
    try:
        variables = scan_directory(Path.cwd())
    except Exception as e:
        console.print(f"[red]Error scanning files:[/red] {e}")
        sys.exit(1)

    if not variables:
        console.print("[yellow]No environment variables found in code.[/yellow]")
        console.print("Make sure you're using env.require() or env.optional() in your code.")
        sys.exit(1)

    # Deduplicate variables
    unique_vars = deduplicate_variables(variables)
    console.print(f"Found {len(unique_vars)} unique environment variable(s)")

    # Generate content
    header = """# Environment Variables
# Generated by TripWire
#
# This file documents all environment variables used in this project.
# Copy this file to .env and fill in your actual values:
#   cp .env.example .env
#
# Never commit .env to version control!

"""

    # Separate required and optional variables
    required_vars = [v for v in unique_vars.values() if v.required]
    optional_vars = [v for v in unique_vars.values() if not v.required]

    sections = []

    if required_vars:
        sections.append("# Required Variables")
        for var in sorted(required_vars, key=lambda v: v.name):
            sections.append(format_var_for_env_example(var))
            sections.append("")

    if optional_vars:
        sections.append("# Optional Variables")
        for var in sorted(optional_vars, key=lambda v: v.name):
            sections.append(format_var_for_env_example(var))
            sections.append("")

    generated_content = header + "\n".join(sections)

    output_path = Path(output)

    # Check mode: compare with existing file
    if check:
        console.print("[yellow]Checking if .env.example is up to date...[/yellow]")
        if not output_path.exists():
            console.print(f"[red][X][/red] {output} does not exist")
            sys.exit(1)

        existing_content = output_path.read_text()
        if existing_content.strip() == generated_content.strip():
            console.print("[green][OK][/green] .env.example is up to date")
        else:
            console.print("[red][X][/red] .env.example is out of date")
            console.print("Run 'tripwire generate --force' to update it")
            sys.exit(1)
        return

    # Check if file exists
    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite.")
        sys.exit(1)

    # Write file
    output_path.write_text(generated_content)
    console.print(f"[green][OK][/green] Generated {output} with {len(unique_vars)} variable(s)")

    # Show breakdown
    if required_vars:
        console.print(f"  - {len(required_vars)} required")
    if optional_vars:
        console.print(f"  - {len(optional_vars)} optional")


@main.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to check",
)
@click.option(
    "--example",
    type=click.Path(exists=True),
    default=".env.example",
    help=".env.example file to compare against",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with error if differences found",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output results as JSON",
)
def check(env_file: str, example: str, strict: bool, output_json: bool) -> None:
    """Check .env file for missing or extra variables.

    Compares your .env file against .env.example to detect drift
    and ensure all required variables are set.
    """
    from rich.table import Table

    from tripwire.parser import compare_env_files

    env_path = Path(env_file)
    example_path = Path(example)

    # Validate files exist
    if not example_path.exists():
        console.print(f"[red]Error:[/red] {example} not found")
        sys.exit(1)

    # Compare files
    missing, extra, common = compare_env_files(env_path, example_path)

    # JSON output mode
    if output_json:
        import json

        result = {
            "status": "ok" if not missing and not extra else "drift",
            "missing": missing,
            "extra": extra,
            "common": common,
        }
        print(json.dumps(result, indent=2))

        if strict and (missing or extra):
            sys.exit(1)
        return

    # Human-readable output
    console.print(f"\nComparing [cyan]{env_file}[/cyan] against [cyan]{example}[/cyan]\n")

    has_issues = False

    # Report missing variables
    if missing:
        has_issues = True
        table = Table(title="Missing Variables", show_header=True, header_style="bold red")
        table.add_column("Variable", style="red")
        table.add_column("Status", style="red")

        for var in missing:
            table.add_row(var, "Not set in .env")

        console.print(table)
        console.print()

    # Report extra variables
    if extra:
        has_issues = True
        table = Table(title="Extra Variables", show_header=True, header_style="bold yellow")
        table.add_column("Variable", style="yellow")
        table.add_column("Status", style="yellow")

        for var in extra:
            table.add_row(var, "Not in .env.example")

        console.print(table)
        console.print()

    # Summary
    if has_issues:
        console.print(f"[yellow]Found {len(missing)} missing and {len(extra)} extra variable(s)[/yellow]")

        if missing:
            console.print("\nTo add missing variables:")
            console.print("  [cyan]tripwire sync[/cyan]")

        if strict:
            sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} No drift detected - .env is in sync with .env.example")
        console.print(f"  {len(common)} variable(s) present in both files")


@main.command()
@click.option(
    "--env-file",
    type=click.Path(),
    default=".env",
    help=".env file to sync",
)
@click.option(
    "--example",
    type=click.Path(exists=True),
    default=".env.example",
    help=".env.example to sync from",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show changes without applying",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Confirm each change",
)
def sync(env_file: str, example: str, dry_run: bool, interactive: bool) -> None:
    """Synchronize .env with .env.example.

    Updates your .env file to match the structure of .env.example,
    adding missing variables and optionally removing extra ones.
    """
    from tripwire.parser import compare_env_files, merge_env_files, parse_env_file

    env_path = Path(env_file)
    example_path = Path(example)

    # Validate example file exists
    if not example_path.exists():
        console.print(f"[red]Error:[/red] {example} not found")
        sys.exit(1)

    # Compare files
    missing, extra, common = compare_env_files(env_path, example_path)

    if not missing and not extra:
        status = get_status_icon("valid")
        console.print(f"{status} Already in sync - no changes needed")
        return

    console.print(f"\nSynchronizing [cyan]{env_file}[/cyan] with [cyan]{example}[/cyan]\n")

    # Show what will be done
    changes_made = False

    if missing:
        console.print(f"[yellow]Will add {len(missing)} missing variable(s):[/yellow]")
        for var in missing:
            console.print(f"  + {var}")
        console.print()
        changes_made = True

    if extra:
        console.print(f"[blue]Found {len(extra)} extra variable(s) (will be kept):[/blue]")
        for var in extra:
            console.print(f"  ~ {var}")
        console.print()

    if not changes_made:
        console.print("[green]No changes needed[/green]")
        return

    if dry_run:
        console.print("[yellow]Dry run - no changes applied[/yellow]")
        console.print("Run without --dry-run to apply changes")
        return

    if interactive:
        import click

        if not click.confirm("Apply these changes?"):
            console.print("Sync cancelled")
            return

    # Get values from example file
    example_vars = parse_env_file(example_path)
    new_vars = {var: example_vars[var] for var in missing}

    # Merge into env file
    merged_content = merge_env_files(env_path, new_vars, preserve_existing=True)

    # Write updated file
    env_path.write_text(merged_content)

    console.print(f"[green][OK][/green] Synchronized {env_file}")
    console.print(f"  Added {len(missing)} variable(s)")
    console.print("\n[yellow]Note:[/yellow] Fill in values for new variables in .env")


@main.command()
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
    """Scan for secrets in git history.

    Detects potential secrets (API keys, tokens, passwords) in your
    git repository to prevent accidental commits.
    """
    from rich.table import Table

    from tripwire.secrets import get_severity_color, scan_env_file, scan_git_history

    console.print("[yellow]Scanning for secrets...[/yellow]\n")

    # Scan current .env file
    env_path = Path(".env")
    findings = []

    if env_path.exists():
        console.print("Scanning .env file...")
        env_findings = scan_env_file(env_path)
        findings.extend(env_findings)

        if env_findings:
            status = get_status_icon("invalid")
            console.print(f"{status} Found {len(env_findings)} potential secret(s) in .env\n")
        else:
            status = get_status_icon("valid")
            console.print(f"{status} No secrets found in .env\n")

    # Scan git history
    if Path(".git").exists():
        console.print(f"Scanning last {depth} commits in git history...")
        git_findings = scan_git_history(Path.cwd(), depth=depth)

        if git_findings:
            console.print(f"[red]Found {len(git_findings)} potential secret(s) in git history[/red]\n")

            # Show unique findings
            seen = set()
            for finding in git_findings:
                key = (finding["variable"], finding["type"])
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        type(
                            "GitFinding",
                            (),
                            {
                                "secret_type": type("Type", (), {"value": finding["type"]})(),
                                "variable_name": finding["variable"],
                                "value": "***",
                                "severity": finding["severity"],
                                "recommendation": f"Found in commit {finding['commit']}. Rotate this secret immediately.",
                            },
                        )()
                    )
        else:
            status = get_status_icon("valid")
            console.print(f"{status} No secrets found in git history\n")

    # Display findings
    if findings:
        table = Table(title="Detected Secrets", show_header=True, header_style="bold red")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Recommendation")

        for finding in findings:
            severity_color = get_severity_color(finding.severity)
            table.add_row(
                finding.variable_name,
                finding.secret_type.value,
                f"[{severity_color}]{finding.severity.upper()}[/{severity_color}]",
                finding.recommendation[:80] + "..." if len(finding.recommendation) > 80 else finding.recommendation,
            )

        console.print(table)
        console.print()

        # Summary
        console.print(f"[red]Total: {len(findings)} potential secret(s) detected[/red]")
        console.print("\n[yellow]Recommendations:[/yellow]")
        console.print("  1. Rotate all detected secrets immediately")
        console.print("  2. Use a secret manager (AWS Secrets Manager, Vault, etc.)")
        console.print("  3. Never commit secrets to version control")
        console.print("  4. Add .env to .gitignore (if not already)")

        if strict:
            sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} No secrets detected")
        console.print("Your environment files appear secure")


def _display_combined_timeline(
    results: List[Tuple[Any, Any]],
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
    timeline: Any,
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
        by_date: Dict[str, List[Any]] = defaultdict(list)
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
            syntax = Syntax(step.command, "bash", theme="monokai", line_numbers=False)
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


@main.command()
@click.argument("secret_name", required=False)
@click.option(
    "--all",
    "scan_all",
    is_flag=True,
    help="Auto-detect and audit all secrets in current .env file",
)
@click.option(
    "--value",
    help="Actual secret value to search for (more accurate)",
)
@click.option(
    "--max-commits",
    default=1000,
    type=int,
    help="Maximum commits to analyze",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def audit(
    secret_name: Optional[str],
    scan_all: bool,
    value: Optional[str],
    max_commits: int,
    output_json: bool,
) -> None:
    """Audit git history for secret leaks.

    Shows when a secret was added, committed, pushed, and provides
    remediation steps to remove it from git history.

    Examples:

        tripwire audit --all

        tripwire audit AWS_SECRET_ACCESS_KEY

        tripwire audit API_KEY --value "sk-abc123..."

        tripwire audit DATABASE_URL --json
    """
    import json

    from rich.table import Table

    from tripwire.git_audit import (
        GitAuditError,
        analyze_secret_history,
        generate_remediation_steps,
    )
    from tripwire.secrets import scan_env_file

    # Validate arguments
    if not scan_all and not secret_name:
        console.print("[red]Error:[/red] Must provide SECRET_NAME or use --all flag")
        console.print("Try: tripwire audit --help")
        sys.exit(1)

    if scan_all and secret_name:
        console.print("[red]Error:[/red] Cannot use both SECRET_NAME and --all flag")
        console.print("Use either 'tripwire audit SECRET_NAME' or 'tripwire audit --all'")
        sys.exit(1)

    # Auto-detection mode
    if scan_all:
        if not output_json:
            console.print("\n[bold cyan][*] Auto-detecting secrets in .env file...[/bold cyan]\n")

        env_file = Path.cwd() / ".env"
        if not env_file.exists():
            console.print("[red]Error:[/red] .env file not found in current directory")
            console.print("Run 'tripwire init' to create one, or specify a secret name to audit.")
            sys.exit(1)

        # Scan .env file for secrets
        detected_secrets = scan_env_file(env_file)

        if not detected_secrets:
            # JSON output mode - return empty results as JSON
            if output_json:
                json_output = {
                    "total_secrets_found": 0,
                    "secrets": [],
                }
                print(json.dumps(json_output, indent=2))
                return

            # Human-readable output
            status = get_status_icon("valid")
            console.print(f"{status} No secrets detected in .env file")
            console.print("Your environment file appears secure")
            return

        # Display detected secrets summary (only in non-JSON mode)
        if not output_json:
            console.print(f"[yellow][!] Found {len(detected_secrets)} potential secret(s) in .env file[/yellow]\n")

            summary_table = Table(title="Detected Secrets", show_header=True, header_style="bold cyan")
            summary_table.add_column("Variable", style="yellow")
            summary_table.add_column("Type", style="cyan")
            summary_table.add_column("Severity", style="red")

            for secret in detected_secrets:
                summary_table.add_row(
                    secret.variable_name,
                    secret.secret_type.value,
                    secret.severity.upper(),
                )

            console.print(summary_table)
            console.print()

        # Audit each detected secret
        all_results = []
        for secret in detected_secrets:
            if not output_json:
                console.print(f"\n[bold cyan]{'=' * 70}[/bold cyan]")
                console.print(f"[bold cyan]Auditing: {secret.variable_name}[/bold cyan]")
                console.print(f"[bold cyan]{'=' * 70}[/bold cyan]\n")

            try:
                timeline = analyze_secret_history(
                    secret_name=secret.variable_name,
                    secret_value=None,  # Don't pass value for privacy
                    repo_path=Path.cwd(),
                    max_commits=max_commits,
                )
                all_results.append((secret, timeline))

            except GitAuditError as e:
                if not output_json:
                    console.print(f"[red]Error auditing {secret.variable_name}:[/red] {e}")
                continue

        # JSON output mode (skip visual output)
        if output_json:
            json_output = {
                "total_secrets_found": len(detected_secrets),
                "secrets": [
                    {
                        "variable_name": secret.variable_name,
                        "secret_type": secret.secret_type.value,
                        "severity": secret.severity,
                        "status": "LEAKED" if timeline.total_occurrences > 0 else "CLEAN",
                        "first_seen": timeline.first_seen.isoformat() if timeline.first_seen else None,
                        "last_seen": timeline.last_seen.isoformat() if timeline.last_seen else None,
                        "commits_affected": len(timeline.commits_affected),
                        "files_affected": timeline.files_affected,
                        "branches_affected": timeline.branches_affected,
                        "is_public": timeline.is_in_public_repo,
                        "is_current": timeline.is_currently_in_git,
                    }
                    for secret, timeline in all_results
                ],
            }
            print(json.dumps(json_output, indent=2))
            return

        # Display combined visual timeline first
        if all_results:
            _display_combined_timeline(all_results, console)

        # Then display individual results
        for secret, timeline in all_results:
            _display_single_audit_result(secret.variable_name, timeline, console)

        return

    # Single secret mode
    try:
        console.print(f"\n[bold cyan]Analyzing git history for: {secret_name}[/bold cyan]\n")
        console.print("[yellow]This may take a moment...[/yellow]\n")

        timeline = analyze_secret_history(
            secret_name=secret_name,
            secret_value=value,
            repo_path=Path.cwd(),
            max_commits=max_commits,
        )

    except GitAuditError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # JSON output mode
    if output_json:
        remediation_steps = generate_remediation_steps(timeline, secret_name)

        result = {
            "secret_name": secret_name,
            "status": "LEAKED" if timeline.total_occurrences > 0 else "CLEAN",
            "first_seen": timeline.first_seen.isoformat() if timeline.first_seen else None,
            "last_seen": timeline.last_seen.isoformat() if timeline.last_seen else None,
            "exposure_duration_days": timeline.exposure_duration_days,
            "commits_affected": len(timeline.commits_affected),
            "files_affected": timeline.files_affected,
            "is_public": timeline.is_in_public_repo,
            "is_current": timeline.is_currently_in_git,
            "severity": timeline.severity,
            "branches_affected": timeline.branches_affected,
            "remediation_steps": [
                {
                    "order": step.order,
                    "title": step.title,
                    "description": step.description,
                    "urgency": step.urgency,
                    "command": step.command,
                    "warning": step.warning,
                }
                for step in remediation_steps
            ],
        }

        print(json.dumps(result, indent=2))
        return

    # Display single secret result using helper function
    _display_single_audit_result(secret_name, timeline, console)


@main.command()
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to validate",
)
def validate(env_file: str) -> None:
    """Validate environment variables without running app.

    Loads and validates all environment variables to ensure they
    meet requirements before starting the application.
    """
    from tripwire.scanner import deduplicate_variables, scan_directory

    env_path = Path(env_file)

    if not env_path.exists():
        console.print(f"[red]Error:[/red] {env_file} not found")
        sys.exit(1)

    console.print(f"[yellow]Validating {env_file}...[/yellow]\n")

    # Scan code for required variables
    console.print("Scanning code for environment variable requirements...")
    try:
        variables = scan_directory(Path.cwd())
    except Exception as e:
        console.print(f"[red]Error scanning code:[/red] {e}")
        sys.exit(1)

    if not variables:
        console.print("[yellow]No environment variables found in code[/yellow]")
        console.print("Nothing to validate")
        return

    # Load the env file
    from dotenv import load_dotenv

    load_dotenv(env_path)

    # Check each required variable
    import os

    unique_vars = deduplicate_variables(variables)
    required_vars = [v for v in unique_vars.values() if v.required]
    optional_vars = [v for v in unique_vars.values() if not v.required]

    console.print(
        f"Found {len(unique_vars)} variable(s): {len(required_vars)} required, {len(optional_vars)} optional\n"
    )

    missing = []
    invalid = []

    for var in required_vars:
        if not os.getenv(var.name):
            missing.append(var.name)

    # Display results
    if missing:
        from rich.table import Table

        table = Table(title="Missing Required Variables", show_header=True, header_style="bold red")
        table.add_column("Variable", style="red")
        table.add_column("Type", style="yellow")

        for var_name in missing:
            var = unique_vars[var_name]
            table.add_row(var_name, var.var_type)

        console.print(table)
        console.print()
        status = get_status_icon("invalid")
        console.print(f"{status} [red]Validation failed:[/red] {len(missing)} required variable(s) missing")
        console.print("\nAdd these variables to your .env file")
        sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} All required variables are set")
        console.print(f"  {len(required_vars)} required variable(s) validated")
        if optional_vars:
            console.print(f"  {len(optional_vars)} optional variable(s) available")


@main.command()
@click.option(
    "--format",
    type=click.Choice(["markdown", "html", "json"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout)",
)
def docs(format: str, output: Optional[str]) -> None:
    """Generate documentation for environment variables.

    Creates documentation in markdown, HTML, or JSON format
    describing all environment variables used in the project.
    """
    from tripwire.scanner import deduplicate_variables, scan_directory

    console.print("[yellow]Scanning code for environment variables...[/yellow]")

    # Scan code
    try:
        variables = scan_directory(Path.cwd())
    except Exception as e:
        console.print(f"[red]Error scanning code:[/red] {e}")
        sys.exit(1)

    if not variables:
        console.print("[yellow]No environment variables found in code[/yellow]")
        sys.exit(1)

    unique_vars = deduplicate_variables(variables)
    console.print(f"Found {len(unique_vars)} unique variable(s)\n")

    # Generate documentation
    if format == "markdown":
        doc_content = generate_markdown_docs(unique_vars)
    elif format == "html":
        doc_content = generate_html_docs(unique_vars)
    else:  # json
        doc_content = generate_json_docs(unique_vars)

    # Output
    if output:
        output_path = Path(output)
        output_path.write_text(doc_content)
        console.print(f"[green][OK][/green] Documentation written to {output}")
    else:
        if format == "markdown":
            # Use rich for nice terminal rendering
            from rich.markdown import Markdown

            console.print(Markdown(doc_content))
        else:
            print(doc_content)


def generate_markdown_docs(variables: Dict[str, Any]) -> str:
    """Generate markdown documentation.

    Args:
        variables: Dictionary of variable information

    Returns:
        Markdown formatted documentation
    """
    from tripwire.scanner import EnvVarInfo, format_default_value

    lines = [
        "# Environment Variables",
        "",
        "This document describes all environment variables used in this project.",
        "",
        "## Required Variables",
        "",
        "| Variable | Type | Description | Validation |",
        "|----------|------|-------------|------------|",
    ]

    required_vars = sorted([v for v in variables.values() if v.required], key=lambda v: v.name)

    if not required_vars:
        lines.append("| - | - | - | - |")
    else:
        for var in required_vars:
            validation = []
            if var.format:
                validation.append(f"Format: {var.format}")
            if var.choices:
                validation.append(f"Choices: {', '.join(str(c) for c in var.choices)}")
            if var.pattern:
                validation.append(f"Pattern: `{var.pattern}`")

            validation_str = "; ".join(validation) if validation else "-"
            desc = var.description or "-"

            lines.append(f"| `{var.name}` | {var.var_type} | {desc} | {validation_str} |")

    lines.extend(
        [
            "",
            "## Optional Variables",
            "",
            "| Variable | Type | Default | Description | Validation |",
            "|----------|------|---------|-------------|------------|",
        ]
    )

    optional_vars = sorted([v for v in variables.values() if not v.required], key=lambda v: v.name)

    if not optional_vars:
        lines.append("| - | - | - | - | - |")
    else:
        for var in optional_vars:
            validation = []
            if var.format:
                validation.append(f"Format: {var.format}")
            if var.choices:
                validation.append(f"Choices: {', '.join(str(c) for c in var.choices)}")
            if var.pattern:
                validation.append(f"Pattern: `{var.pattern}`")

            validation_str = "; ".join(validation) if validation else "-"
            desc = var.description or "-"
            default_str = format_default_value(var.default) or "-"

            lines.append(f"| `{var.name}` | {var.var_type} | `{default_str}` | {desc} | {validation_str} |")

    lines.extend(
        [
            "",
            "## Usage",
            "",
            "To use these variables in your Python code:",
            "",
            "```python",
            "from tripwire import env",
            "",
            "# Required variable",
            "api_key = env.require('API_KEY', description='API key for service')",
            "",
            "# Optional variable with default",
            "debug = env.optional('DEBUG', default=False, type=bool)",
            "```",
            "",
            "---",
            "",
            "*Generated by [TripWire](https://github.com/Daily-Nerd/TripWire)*",
        ]
    )

    return "\n".join(lines)


def generate_html_docs(variables: Dict[str, Any]) -> str:
    """Generate HTML documentation.

    Args:
        variables: Dictionary of variable information

    Returns:
        HTML formatted documentation
    """
    from tripwire.scanner import format_default_value

    required_vars = sorted([v for v in variables.values() if v.required], key=lambda v: v.name)
    optional_vars = sorted([v for v in variables.values() if not v.required], key=lambda v: v.name)

    html = """<!DOCTYPE html>
<html>
<head>
    <title>Environment Variables Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border: 1px solid #ddd; }
        th { background-color: #f5f5f5; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        code { background-color: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
        .required { color: #c00; }
        .optional { color: #060; }
    </style>
</head>
<body>
    <h1>Environment Variables</h1>
    <p>This document describes all environment variables used in this project.</p>
"""

    html += "    <h2>Required Variables</h2>\n"
    html += "    <table>\n"
    html += "        <tr><th>Variable</th><th>Type</th><th>Description</th><th>Validation</th></tr>\n"

    for var in required_vars:
        validation = []
        if var.format:
            validation.append(f"Format: {var.format}")
        if var.choices:
            validation.append(f"Choices: {', '.join(str(c) for c in var.choices)}")
        validation_str = "; ".join(validation) if validation else "-"
        desc = var.description or "-"

        html += f"        <tr><td><code>{var.name}</code></td><td>{var.var_type}</td><td>{desc}</td><td>{validation_str}</td></tr>\n"

    html += "    </table>\n"

    html += "    <h2>Optional Variables</h2>\n"
    html += "    <table>\n"
    html += "        <tr><th>Variable</th><th>Type</th><th>Default</th><th>Description</th><th>Validation</th></tr>\n"

    for var in optional_vars:
        validation = []
        if var.format:
            validation.append(f"Format: {var.format}")
        if var.choices:
            validation.append(f"Choices: {', '.join(str(c) for c in var.choices)}")
        validation_str = "; ".join(validation) if validation else "-"
        desc = var.description or "-"
        default_str = format_default_value(var.default) or "-"

        html += f"        <tr><td><code>{var.name}</code></td><td>{var.var_type}</td><td><code>{default_str}</code></td><td>{desc}</td><td>{validation_str}</td></tr>\n"

    html += "    </table>\n"
    html += """
    <hr>
    <p><em>Generated by <a href="https://github.com/Daily-Nerd/TripWire">TripWire</a></em></p>
</body>
</html>
"""

    return html


def generate_json_docs(variables: Dict[str, Any]) -> str:
    """Generate JSON documentation.

    Args:
        variables: Dictionary of variable information

    Returns:
        JSON formatted documentation
    """
    import json

    doc = {"variables": []}

    for var in sorted(variables.values(), key=lambda v: v.name):
        var_doc = {
            "name": var.name,
            "type": var.var_type,
            "required": var.required,
            "default": var.default,
            "description": var.description,
            "secret": var.secret,
        }

        if var.format:
            var_doc["format"] = var.format
        if var.pattern:
            var_doc["pattern"] = var.pattern
        if var.choices:
            var_doc["choices"] = var.choices
        if var.min_val is not None:
            var_doc["min_value"] = var.min_val
        if var.max_val is not None:
            var_doc["max_value"] = var.max_val

        doc["variables"].append(var_doc)

    return json.dumps(doc, indent=2)


@main.group()
def schema() -> None:
    """Manage TripWire configuration schema (.tripwire.toml).

    Configuration as Code - define environment variables declaratively
    with type validation, format checking, and environment-specific defaults.
    """
    pass


@schema.command("init")
def schema_init() -> None:
    """Create a starter .tripwire.toml schema file.

    Generates a template configuration schema that you can customize
    for your project's environment variables.
    """
    schema_path = Path(".tripwire.toml")

    if schema_path.exists():
        console.print("[yellow][!] .tripwire.toml already exists[/yellow]")
        if not click.confirm("Overwrite existing file?"):
            console.print("Schema initialization cancelled")
            return

    # Create starter schema
    starter_content = """# TripWire Configuration Schema
# Define your environment variables with validation rules

[project]
name = "my-project"
version = "0.1.0"
description = "Project description"

[validation]
strict = true  # Fail on unknown variables
allow_missing_optional = true
warn_unused = true

[security]
entropy_threshold = 4.5
scan_git_history = true
exclude_patterns = ["TEST_*", "EXAMPLE_*"]

# Example variable definitions
# Uncomment and customize for your project

# [variables.DATABASE_URL]
# type = "string"
# required = true
# format = "postgresql"
# description = "PostgreSQL database connection"
# secret = true
# examples = ["postgresql://localhost:5432/dev"]

# [variables.DEBUG]
# type = "bool"
# required = false
# default = false
# description = "Enable debug mode"

# [variables.PORT]
# type = "int"
# required = false
# default = 8000
# min = 1024
# max = 65535
# description = "Server port"

# Environment-specific defaults
[environments.development]
# DATABASE_URL = "postgresql://localhost:5432/dev"
# DEBUG = true

[environments.production]
# DEBUG = false
# strict_secrets = true
"""

    schema_path.write_text(starter_content)
    console.print("[green][OK][/green] Created .tripwire.toml")
    console.print("\nNext steps:")
    console.print("  1. Edit .tripwire.toml to define your environment variables")
    console.print("  2. Run [cyan]tripwire schema validate[/cyan] to check your .env file")
    console.print("  3. Run [cyan]tripwire schema generate-example[/cyan] to create .env.example from schema")


@schema.command("validate")
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to validate",
)
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    default=".tripwire.toml",
    help="Schema file to validate against",
)
@click.option(
    "--environment",
    "-e",
    default="development",
    help="Environment name (development, production, etc.)",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit with error if validation fails",
)
def schema_validate(env_file: str, schema_file: str, environment: str, strict: bool) -> None:
    """Validate .env file against schema.

    Checks that all required variables are present and validates
    types, formats, and constraints defined in .tripwire.toml.
    """
    from rich.table import Table

    from tripwire.schema import validate_with_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema init[/cyan] to create one")
        sys.exit(1)

    console.print(f"[yellow]Validating {env_file} against {schema_file}...[/yellow]\n")
    console.print(f"Environment: [cyan]{environment}[/cyan]\n")

    is_valid, errors = validate_with_schema(env_file, schema_file, environment)

    if is_valid:
        status = get_status_icon("valid")
        console.print(f"{status} [green]Validation passed![/green]")
        console.print("All environment variables are valid")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} [red]Validation failed with {len(errors)} error(s):[/red]\n")

        table = Table(title="Validation Errors", show_header=True, header_style="bold red")
        table.add_column("Error", style="red")

        for error in errors:
            table.add_row(error)

        console.print(table)

        if strict:
            sys.exit(1)


@schema.command("generate-example")
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    default=".tripwire.toml",
    help="Schema file to generate from",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".env.example",
    help="Output file",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing file",
)
def schema_generate_example(schema_file: str, output: str, force: bool) -> None:
    """Generate .env.example from schema.

    Creates a .env.example file from your .tripwire.toml schema,
    including descriptions, examples, and validation rules.
    """
    from tripwire.schema import load_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema init[/cyan] to create one")
        sys.exit(1)

    output_path = Path(output)
    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite")
        sys.exit(1)

    console.print(f"[yellow]Generating .env.example from {schema_file}...[/yellow]\n")

    schema = load_schema(schema_path)
    if not schema:
        console.print("[red]Error:[/red] Failed to load schema")
        sys.exit(1)

    env_example_content = schema.generate_env_example()
    output_path.write_text(env_example_content)

    console.print(f"[green][OK][/green] Generated {output}")
    console.print(f"  {len(schema.variables)} variable(s) defined")


@schema.command("import")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=".tripwire.toml",
    help="Output schema file",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing file",
)
def schema_import(output: str, force: bool) -> None:
    """Generate .tripwire.toml from code scanning.

    Scans Python files for env.require() and env.optional() calls
    and generates a schema file automatically.
    """
    from datetime import datetime

    from tripwire.scanner import deduplicate_variables, scan_directory

    output_path = Path(output)

    # Check if file exists
    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite")
        sys.exit(1)

    console.print("[yellow]Scanning Python files for environment variables...[/yellow]")

    # Scan current directory
    try:
        variables = scan_directory(Path.cwd())
    except Exception as e:
        console.print(f"[red]Error scanning files:[/red] {e}")
        sys.exit(1)

    if not variables:
        console.print("[yellow]No environment variables found in code[/yellow]")
        console.print("Make sure you're using env.require() or env.optional() in your code.")
        sys.exit(1)

    # Deduplicate
    unique_vars = deduplicate_variables(variables)
    console.print(f"Found {len(unique_vars)} unique variable(s)")

    # Count required vs optional
    required_count = sum(1 for v in unique_vars.values() if v.required)
    optional_count = len(unique_vars) - required_count

    console.print(f"\nGenerating {output}...\n")

    # Generate TOML content
    lines = [
        "# Auto-generated by TripWire schema import",
        f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "# Review and customize this schema for your project",
        "",
        "[project]",
        'name = "your-project"',
        'version = "0.1.0"',
        'description = "Generated from code scanning"',
        "",
        "[validation]",
        "strict = true",
        "allow_missing_optional = true",
        "",
        "[security]",
        "entropy_threshold = 4.5",
        "scan_git_history = true",
        "",
        "# Variables discovered from code",
        "",
    ]

    # Add variables sorted by name
    for var_name in sorted(unique_vars.keys()):
        var = unique_vars[var_name]

        lines.append(f"[variables.{var_name}]")

        # Type
        lines.append(f'type = "{var.var_type}"')

        # Required
        lines.append(f"required = {str(var.required).lower()}")

        # Default
        if var.default is not None:
            if isinstance(var.default, str):
                lines.append(f'default = "{var.default}"')
            elif isinstance(var.default, bool):
                lines.append(f"default = {str(var.default).lower()}")
            else:
                lines.append(f"default = {var.default}")

        # Description
        if var.description:
            # Escape quotes in description
            desc = var.description.replace('"', '\\"')
            lines.append(f'description = "{desc}"')

        # Secret
        if var.secret:
            lines.append("secret = true")

        # Format
        if var.format:
            lines.append(f'format = "{var.format}"')

        # Pattern
        if var.pattern:
            # Escape backslashes for TOML
            pattern = var.pattern.replace("\\", "\\\\")
            lines.append(f'pattern = "{pattern}"')

        # Choices
        if var.choices:
            choices_str = ", ".join(f'"{c}"' for c in var.choices)
            lines.append(f"choices = [{choices_str}]")

        # Min/Max
        if var.min_val is not None:
            lines.append(f"min = {var.min_val}")
        if var.max_val is not None:
            lines.append(f"max = {var.max_val}")

        # Add source comment
        lines.append(f"# Found in: {var.file_path}:{var.line_number}")

        lines.append("")  # Blank line between variables

    # Write file
    output_path.write_text("\n".join(lines))

    status = get_status_icon("valid")
    console.print(f"{status} [green]Generated {output} with {len(unique_vars)} variable(s)[/green]")
    console.print(f"  - {required_count} required")
    console.print(f"  - {optional_count} optional")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print(f"  1. Review {output} and customize as needed")
    console.print("  2. Run: [cyan]tripwire schema validate[/cyan]")


@schema.command("check")
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    default=".tripwire.toml",
    help="Schema file to validate",
)
def schema_check(schema_file: str) -> None:
    """Validate .tripwire.toml syntax and structure.

    Checks that the schema file is valid TOML, all format validators
    exist, and environment references are valid.
    """
    import tomllib

    from rich.table import Table

    schema_path = Path(schema_file)

    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema init[/cyan] to create one")
        sys.exit(1)

    console.print(f"\nChecking [cyan]{schema_file}[/cyan]...\n")

    errors = []
    warnings = []

    # Check 1: TOML syntax
    try:
        with open(schema_path, "rb") as f:
            data = tomllib.load(f)
        status = get_status_icon("valid")
        console.print(f"{status} TOML syntax is valid")
    except tomllib.TOMLDecodeError as e:
        status = get_status_icon("invalid")
        console.print(f"{status} TOML syntax error: {e}")
        errors.append(f"TOML syntax error: {e}")
        # Can't continue if TOML is invalid
        console.print(f"\n[red][X][/red] Schema validation failed")
        console.print(f"  {len(errors)} error(s) found\n")
        console.print("Fix TOML syntax errors and run again.")
        sys.exit(1)

    # Check 2: Schema structure (required sections)
    has_structure_error = False
    if "project" not in data:
        warnings.append("Missing [project] section (recommended)")

    if "variables" not in data:
        errors.append("Missing [variables] section - no variables defined")
        has_structure_error = True

    if not has_structure_error:
        status = get_status_icon("valid")
        console.print(f"{status} Schema structure is valid")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} Schema structure issues found")

    # Check 3: Format validators
    valid_formats = {"email", "url", "postgresql", "uuid", "ipv4"}
    format_errors = []

    if "variables" in data:
        for var_name, var_config in data["variables"].items():
            if "format" in var_config:
                fmt = var_config["format"]
                if fmt not in valid_formats:
                    format_errors.append(
                        f"variables.{var_name}: Unknown format '{fmt}' " f"(valid: {', '.join(sorted(valid_formats))})"
                    )

    if not format_errors:
        status = get_status_icon("valid")
        console.print(f"{status} All format validators exist")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} Format validator issues found")
        errors.extend(format_errors)

    # Check 4: Type values
    valid_types = {"string", "int", "float", "bool", "list", "dict"}
    type_errors = []

    if "variables" in data:
        for var_name, var_config in data["variables"].items():
            if "type" in var_config:
                var_type = var_config["type"]
                if var_type not in valid_types:
                    type_errors.append(
                        f"variables.{var_name}: Unknown type '{var_type}' " f"(valid: {', '.join(sorted(valid_types))})"
                    )

    if not type_errors:
        status = get_status_icon("valid")
        console.print(f"{status} All type values are valid")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} Type value issues found")
        errors.extend(type_errors)

    # Check 5: Environment references
    env_errors = []
    defined_vars = set(data.get("variables", {}).keys())

    if "environments" in data:
        for env_name, env_config in data["environments"].items():
            if isinstance(env_config, dict):
                for var_name in env_config.keys():
                    # Skip special keys like strict_secrets
                    if var_name.startswith("strict_"):
                        continue
                    if var_name not in defined_vars:
                        env_errors.append(f"environments.{env_name}.{var_name}: " f"References undefined variable")

    if not env_errors:
        status = get_status_icon("valid")
        console.print(f"{status} Environment references are valid")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} Environment reference issues found")
        errors.extend(env_errors)

    # Check 6: Best practices
    if "variables" in data:
        for var_name, var_config in data["variables"].items():
            if "description" not in var_config or not var_config["description"]:
                warnings.append(f"variables.{var_name}: Missing description (best practice)")

            if var_config.get("secret") and "examples" in var_config:
                warnings.append(f"variables.{var_name}: Secret variable has examples " "(avoid showing real secrets)")

    # Display errors and warnings
    console.print()

    if errors:
        table = Table(title="Errors", show_header=True, header_style="bold red")
        table.add_column("Error", style="red")

        for error in errors:
            table.add_row(error)

        console.print(table)
        console.print()

    if warnings:
        table = Table(title="Warnings", show_header=True, header_style="bold yellow")
        table.add_column("Warning", style="yellow")

        for warning in warnings[:10]:  # Limit to 10 warnings
            table.add_row(warning)

        if len(warnings) > 10:
            console.print(f"\n  ... and {len(warnings) - 10} more warning(s)")

        console.print(table)
        console.print()

    # Summary
    if errors:
        status = get_status_icon("invalid")
        console.print(f"{status} [red]Schema validation failed[/red]")
        console.print(f"  {len(errors)} error(s) found")
        if warnings:
            console.print(f"  {len(warnings)} warning(s)")
        console.print("\nFix these issues and run again.")
        sys.exit(1)
    else:
        status = get_status_icon("valid")
        console.print(f"{status} [green]Schema is valid[/green]")
        if warnings:
            console.print(f"  {len(warnings)} warning(s) (non-blocking)")


@schema.command("generate-env")
@click.option(
    "--environment",
    "-e",
    default="development",
    help="Environment name (development, staging, production)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output .env file [default: .env.{environment}]",
)
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    default=".tripwire.toml",
    help="Schema file to generate from",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Prompt for secret values",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing file",
)
@click.option(
    "--validate",
    is_flag=True,
    default=True,
    help="Validate after generation [default: true]",
)
@click.option(
    "--format-output",
    type=click.Choice(["env", "json", "yaml"]),
    default="env",
    help="Output format",
)
def schema_generate_env(
    environment: str,
    output: Optional[str],
    schema_file: str,
    interactive: bool,
    overwrite: bool,
    validate: bool,
    format_output: str,
) -> None:
    """Generate environment-specific .env file from schema.

    Creates a .env file for a specific environment using defaults
    from .tripwire.toml. Optionally prompts for secret values.

    Examples:

        tripwire schema generate-env --environment production

        tripwire schema generate-env -e staging -i

        tripwire schema generate-env -e prod --output /tmp/.env.prod
    """
    import json

    from tripwire.schema import load_schema, validate_with_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema init[/cyan] to create one")
        sys.exit(1)

    # Determine output path
    if not output:
        output = f".env.{environment}"
    output_path = Path(output)

    if output_path.exists() and not overwrite:
        console.print(f"[red]Error:[/red] {output} already exists")
        console.print("Use --overwrite to replace it")
        sys.exit(1)

    console.print(f"[yellow]Generating {output} from {schema_file}...[/yellow]\n")
    console.print(f"Environment: [cyan]{environment}[/cyan]\n")

    # Load schema
    schema = load_schema(schema_path)
    if not schema:
        console.print("[red]Error:[/red] Failed to load schema")
        sys.exit(1)

    # Generate content
    if format_output == "env":
        env_content, needs_input = schema.generate_env_for_environment(
            environment=environment,
            interactive=interactive,
        )

        # Interactive mode: prompt for values
        if interactive and needs_input:
            console.print("[bold cyan]Please provide values for the following variables:[/bold cyan]\n")

            # Build replacements for PROMPT_ME placeholders
            replacements = {}
            for var_name, description in needs_input:
                var_schema = schema.variables.get(var_name)
                is_secret = var_schema.secret if var_schema else False

                if is_secret:
                    value = click.prompt(
                        f"{var_name} ({description})",
                        hide_input=True,
                        default="",
                        show_default=False,
                    )
                else:
                    value = click.prompt(
                        f"{var_name} ({description})",
                        default="",
                        show_default=False,
                    )

                replacements[var_name] = value

            # Replace PROMPT_ME values
            for var_name, value in replacements.items():
                env_content = env_content.replace(f"{var_name}=PROMPT_ME", f"{var_name}={value}")

            console.print()

        # Write file
        output_path.write_text(env_content)

        status = get_status_icon("valid")
        console.print(f"{status} [green]Generated {output}[/green]")

        # Count variables
        required_count = len([v for v in schema.variables.values() if v.required])
        optional_count = len([v for v in schema.variables.values() if not v.required])

        console.print(f"  - {required_count} required variable(s)")
        console.print(f"  - {optional_count} optional variable(s)")

        # Show variables requiring manual input
        if needs_input and not interactive:
            console.print(f"\n[yellow]Variables requiring manual input:[/yellow]")
            for var_name, description in needs_input:
                console.print(f"  - {var_name}: {description or 'No description'}")

    elif format_output == "json":
        # Generate JSON format
        env_defaults = schema.get_defaults(environment)
        json_content = json.dumps(env_defaults, indent=2)
        output_path.write_text(json_content)

        console.print(f"[green][OK][/green] Generated {output} (JSON format)")

    elif format_output == "yaml":
        try:
            import yaml
        except ImportError:
            console.print("[red]Error:[/red] PyYAML not installed")
            console.print("Install it with: [cyan]pip install pyyaml[/cyan]")
            sys.exit(1)

        # Generate YAML format
        env_defaults = schema.get_defaults(environment)
        yaml_content = yaml.dump(env_defaults, default_flow_style=False)
        output_path.write_text(yaml_content)

        console.print(f"[green][OK][/green] Generated {output} (YAML format)")

    # Validate after generation
    if validate and format_output == "env":
        console.print(f"\n[yellow]Validating generated file...[/yellow]")

        is_valid, errors = validate_with_schema(output_path, schema_path, environment)

        if is_valid:
            status = get_status_icon("valid")
            console.print(f"{status} [green]Validation passed![/green]")
        else:
            status = get_status_icon("invalid")
            console.print(f"{status} [yellow]Validation warnings:[/yellow]")
            for error in errors:
                console.print(f"  - {error}")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print(f"  1. Review {output} and fill in any missing values")
    if format_output == "env":
        console.print(
            f"  2. Validate: [cyan]tripwire schema validate --env-file {output} --environment {environment}[/cyan]"
        )


@schema.command("docs")
@click.option(
    "--schema-file",
    type=click.Path(exists=True),
    default=".tripwire.toml",
    help="Schema file to document",
)
@click.option(
    "--format",
    type=click.Choice(["markdown", "html"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout)",
)
def schema_docs(schema_file: str, format: str, output: Optional[str]) -> None:
    """Generate documentation from schema.

    Creates comprehensive documentation for your environment variables
    based on the schema definitions in .tripwire.toml.
    """
    from tripwire.schema import load_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        sys.exit(1)

    console.print(f"[yellow]Generating documentation from {schema_file}...[/yellow]\n")

    schema = load_schema(schema_path)
    if not schema:
        console.print("[red]Error:[/red] Failed to load schema")
        sys.exit(1)

    # Generate markdown documentation
    lines = [
        f"# {schema.project_name or 'Project'} - Environment Variables",
        "",
        f"{schema.project_description}" if schema.project_description else "",
        "",
        "## Required Variables",
        "",
    ]

    required_vars = [v for v in schema.variables.values() if v.required]
    optional_vars = [v for v in schema.variables.values() if not v.required]

    if required_vars:
        lines.append("| Variable | Type | Description | Validation |")
        lines.append("|----------|------|-------------|------------|")

        for var in sorted(required_vars, key=lambda v: v.name):
            validation_parts = []
            if var.format:
                validation_parts.append(f"Format: {var.format}")
            if var.pattern:
                validation_parts.append(f"Pattern: `{var.pattern}`")
            if var.choices:
                validation_parts.append(f"Choices: {', '.join(var.choices)}")
            if var.min is not None or var.max is not None:
                range_str = f"Range: {var.min or '-∞'} to {var.max or '∞'}"
                validation_parts.append(range_str)

            validation_str = "; ".join(validation_parts) if validation_parts else "-"
            lines.append(f"| `{var.name}` | {var.type} | {var.description or '-'} | {validation_str} |")
    else:
        lines.append("*No required variables defined*")

    lines.extend(["", "## Optional Variables", ""])

    if optional_vars:
        lines.append("| Variable | Type | Default | Description | Validation |")
        lines.append("|----------|------|---------|-------------|------------|")

        for var in sorted(optional_vars, key=lambda v: v.name):
            validation_parts = []
            if var.format:
                validation_parts.append(f"Format: {var.format}")
            if var.pattern:
                validation_parts.append(f"Pattern: `{var.pattern}`")
            if var.choices:
                validation_parts.append(f"Choices: {', '.join(var.choices)}")

            validation_str = "; ".join(validation_parts) if validation_parts else "-"
            default_str = str(var.default) if var.default is not None else "-"

            lines.append(
                f"| `{var.name}` | {var.type} | `{default_str}` | {var.description or '-'} | {validation_str} |"
            )
    else:
        lines.append("*No optional variables defined*")

    lines.extend(
        [
            "",
            "## Environments",
            "",
        ]
    )

    if schema.environments:
        for env_name in sorted(schema.environments.keys()):
            lines.append(f"### {env_name}")
            lines.append("")
            env_vars = schema.environments[env_name]
            if env_vars:
                for var_name, value in env_vars.items():
                    lines.append(f"- `{var_name}`: `{value}`")
            else:
                lines.append("*No environment-specific settings*")
            lines.append("")
    else:
        lines.append("*No environment-specific configurations*")

    doc_content = "\n".join(lines)

    if output:
        output_path = Path(output)
        output_path.write_text(doc_content)
        console.print(f"[green][OK][/green] Documentation written to {output}")
    else:
        if format == "markdown":
            from rich.markdown import Markdown

            console.print(Markdown(doc_content))
        else:
            print(doc_content)


@schema.command("diff")
@click.argument("schema1", type=click.Path(exists=True))
@click.argument("schema2", type=click.Path(exists=True))
@click.option(
    "--output-format",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format",
)
@click.option(
    "--show-non-breaking",
    is_flag=True,
    help="Include non-breaking changes",
)
def schema_diff(schema1: str, schema2: str, output_format: str, show_non_breaking: bool) -> None:
    """Compare two schema files and show differences.

    Shows added, removed, and modified variables between schema versions.
    Highlights breaking changes that require migration.

    Examples:

        tripwire schema diff .tripwire.toml .tripwire.toml.old

        tripwire schema diff schema-v1.toml schema-v2.toml --output-format json
    """
    import json

    from rich.table import Table

    from tripwire.schema import TripWireSchema
    from tripwire.schema_diff import compare_schemas

    console.print(f"\n[bold cyan]Schema Diff: {schema1} vs {schema2}[/bold cyan]\n")

    # Load schemas
    try:
        old_schema = TripWireSchema.from_toml(schema1)
        new_schema = TripWireSchema.from_toml(schema2)
    except Exception as e:
        console.print(f"[red]Error loading schemas:[/red] {e}")
        sys.exit(1)

    # Compare
    diff = compare_schemas(old_schema, new_schema)

    if output_format == "json":
        # JSON output
        result = {
            "added": [
                {
                    "variable": c.variable_name,
                    "required": c.new_schema.required,
                    "type": c.new_schema.type,
                    "breaking": c.breaking,
                }
                for c in diff.added_variables
            ],
            "removed": [
                {
                    "variable": c.variable_name,
                    "was_required": c.old_schema.required,
                    "type": c.old_schema.type,
                    "breaking": c.breaking,
                }
                for c in diff.removed_variables
            ],
            "modified": [
                {
                    "variable": c.variable_name,
                    "changes": c.changes,
                    "breaking": c.breaking,
                }
                for c in diff.modified_variables
            ],
            "summary": diff.summary(),
        }
        print(json.dumps(result, indent=2))
        return

    if output_format == "markdown":
        # Markdown output
        lines = [
            f"# Schema Diff: {schema1} vs {schema2}",
            "",
        ]

        if diff.added_variables:
            lines.append("## Added Variables")
            lines.append("")
            lines.append("| Variable | Type | Required | Breaking |")
            lines.append("|----------|------|----------|----------|")
            for change in diff.added_variables:
                lines.append(
                    f"| `{change.variable_name}` | {change.new_schema.type} | "
                    f"{'Yes' if change.new_schema.required else 'No'} | "
                    f"{'Yes' if change.breaking else 'No'} |"
                )
            lines.append("")

        if diff.removed_variables:
            lines.append("## Removed Variables")
            lines.append("")
            lines.append("| Variable | Type | Was Required | Breaking |")
            lines.append("|----------|------|--------------|----------|")
            for change in diff.removed_variables:
                lines.append(
                    f"| `{change.variable_name}` | {change.old_schema.type} | "
                    f"{'Yes' if change.old_schema.required else 'No'} | "
                    f"{'Yes' if change.breaking else 'No'} |"
                )
            lines.append("")

        if diff.modified_variables:
            lines.append("## Modified Variables")
            lines.append("")
            for change in diff.modified_variables:
                lines.append(f"### `{change.variable_name}`")
                lines.append("")
                for desc in change.changes:
                    lines.append(f"- {desc}")
                if change.breaking:
                    lines.append(f"- **Breaking**: {', '.join(r.value for r in change.breaking_reasons)}")
                lines.append("")

        print("\n".join(lines))
        return

    # Table output (default)
    summary = diff.summary()

    # Added variables
    if diff.added_variables:
        table = Table(title="Added Variables", show_header=True, header_style="bold green")
        table.add_column("Variable", style="green")
        table.add_column("Type")
        table.add_column("Required")
        table.add_column("Description")

        for change in diff.added_variables:
            table.add_row(
                change.variable_name,
                change.new_schema.type,
                "Yes" if change.new_schema.required else "No",
                change.new_schema.description or "-",
            )

        console.print(table)
        console.print()

    # Removed variables
    if diff.removed_variables:
        table = Table(title="Removed Variables", show_header=True, header_style="bold red")
        table.add_column("Variable", style="red")
        table.add_column("Type")
        table.add_column("Was Required")
        table.add_column("Description")

        for change in diff.removed_variables:
            table.add_row(
                change.variable_name,
                change.old_schema.type,
                "Yes" if change.old_schema.required else "No",
                change.old_schema.description or "-",
            )

        console.print(table)
        console.print()

    # Modified variables
    if diff.modified_variables:
        table = Table(title="Modified Variables", show_header=True, header_style="bold yellow")
        table.add_column("Variable", style="yellow")
        table.add_column("Changes")

        for change in diff.modified_variables:
            if not show_non_breaking and not change.breaking:
                continue

            changes_text = "\n".join(change.changes)
            table.add_row(change.variable_name, changes_text)

        console.print(table)
        console.print()

    # Breaking changes warning
    if diff.has_breaking_changes:
        console.print("[bold red]Breaking Changes Detected:[/bold red]")
        for change in diff.breaking_changes:
            console.print(f"  - {change.variable_name}: {', '.join(change.changes)}")
        console.print()

    # Summary
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Added: {summary['added']}")
    console.print(f"  Removed: {summary['removed']}")
    console.print(f"  Modified: {summary['modified']}")
    console.print(f"  Unchanged: {summary['unchanged']}")
    console.print(f"  Breaking: {summary['breaking']}")

    if diff.has_breaking_changes:
        console.print("\n[yellow]Migration recommended:[/yellow]")
        console.print(f"  Run: [cyan]tripwire schema migrate --from {schema1} --to {schema2}[/cyan]")


@schema.command("migrate")
@click.option(
    "--from",
    "from_schema",
    type=click.Path(exists=True),
    required=True,
    help="Old schema file",
)
@click.option(
    "--to",
    "to_schema",
    type=click.Path(exists=True),
    required=True,
    help="New schema file",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=".env",
    help=".env file to migrate",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show migration plan without applying",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Confirm each change",
)
@click.option(
    "--force",
    is_flag=True,
    help="Apply even with breaking changes",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before migration",
)
def schema_migrate(
    from_schema: str,
    to_schema: str,
    env_file: str,
    dry_run: bool,
    interactive: bool,
    force: bool,
    backup: bool,
) -> None:
    """Migrate .env file between schema versions.

    Updates .env file to match new schema, adding missing variables,
    removing deprecated ones, and converting types where possible.

    Examples:

        tripwire schema migrate --from old.toml --to new.toml

        tripwire schema migrate --from old.toml --to new.toml --dry-run

        tripwire schema migrate --from old.toml --to new.toml --force
    """
    from tripwire.schema_diff import create_migration_plan

    console.print(f"[bold cyan]Migrating {env_file} from schema {from_schema} to {to_schema}...[/bold cyan]\n")

    # Create migration plan
    try:
        plan = create_migration_plan(
            old_schema_path=Path(from_schema),
            new_schema_path=Path(to_schema),
            env_file_path=Path(env_file),
        )
    except Exception as e:
        console.print(f"[red]Error creating migration plan:[/red] {e}")
        sys.exit(1)

    # Check for breaking changes
    if plan.diff.has_breaking_changes and not force:
        console.print("[red]Breaking changes detected:[/red]")
        for change in plan.diff.breaking_changes:
            console.print(f"  - {change.variable_name}: {', '.join(change.changes)}")
        console.print()
        console.print("[yellow]Use --force to proceed with migration[/yellow]")
        sys.exit(1)

    # Show changes
    console.print("[bold]Changes to apply:[/bold]\n")

    if plan.diff.added_variables:
        console.print("[green]Added variables:[/green]")
        for change in plan.diff.added_variables:
            if change.new_schema.default is not None:
                console.print(f"  + {change.variable_name} (default: {change.new_schema.default})")
            else:
                console.print(f"  + {change.variable_name} (needs value)")

    if plan.diff.removed_variables:
        console.print("\n[red]Removed variables:[/red]")
        for change in plan.diff.removed_variables:
            console.print(f"  - {change.variable_name}")

    if plan.diff.modified_variables:
        console.print("\n[yellow]Modified variables:[/yellow]")
        for change in plan.diff.modified_variables:
            console.print(f"  ~ {change.variable_name}: {', '.join(change.changes)}")

    console.print()

    # Dry run mode
    if dry_run:
        console.print("[yellow]Dry run - no changes applied[/yellow]")
        console.print("Run without --dry-run to apply changes")
        return

    # Interactive confirmation
    if interactive:
        if not click.confirm("Apply these changes?"):
            console.print("Migration cancelled")
            return

    # Execute migration
    success, messages = plan.execute(dry_run=False, interactive=interactive)

    if success:
        for msg in messages:
            console.print(msg)

        console.print(f"\n[green]Migration completed successfully![/green]")

        if plan.backup_file:
            console.print(f"Backup saved to: {plan.backup_file}")

        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print(f"  1. Review {env_file} and fill in any CHANGE_ME placeholders")
        console.print(f"  2. Validate: [cyan]tripwire schema validate --schema-file {to_schema}[/cyan]")
    else:
        console.print(f"[red]Migration failed:[/red]")
        for msg in messages:
            console.print(f"  {msg}")
        sys.exit(1)


@main.command("install-hooks")
@click.option(
    "--framework",
    type=click.Choice(["git", "pre-commit"]),
    default="git",
    help="Hook framework to use",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing hooks",
)
@click.option(
    "--uninstall",
    is_flag=True,
    help="Remove TripWire hooks",
)
def install_hooks(framework: str, force: bool, uninstall: bool) -> None:
    """Install pre-commit hooks for TripWire.

    Prevents commits with validation errors or secrets by automatically
    running checks before each commit.

    Examples:

        tripwire install-hooks

        tripwire install-hooks --framework pre-commit

        tripwire install-hooks --uninstall
    """
    import os
    import shutil
    import stat
    from datetime import datetime

    git_dir = Path(".git")

    if not git_dir.exists():
        console.print("[red]Error:[/red] Not a git repository")
        console.print("Initialize git first: [cyan]git init[/cyan]")
        sys.exit(1)

    hooks_dir = git_dir / "hooks"
    pre_commit_hook = hooks_dir / "pre-commit"
    config_file = Path(".tripwire-hooks.toml")

    # Uninstall mode
    if uninstall:
        console.print("[yellow]Uninstalling TripWire hooks...[/yellow]\n")

        removed_files = []

        if pre_commit_hook.exists():
            # Check if it's our hook
            content = pre_commit_hook.read_text()
            if "Generated by TripWire" in content:
                pre_commit_hook.unlink()
                removed_files.append(str(pre_commit_hook))
                console.print(f"[green][OK][/green] Removed {pre_commit_hook}")
            else:
                console.print(f"[yellow][!][/yellow] {pre_commit_hook} not managed by TripWire, skipping")

        if config_file.exists():
            config_file.unlink()
            removed_files.append(str(config_file))
            console.print(f"[green][OK][/green] Removed {config_file}")

        if removed_files:
            console.print(f"\n[green]Successfully removed {len(removed_files)} file(s)[/green]")
        else:
            console.print("[yellow]No TripWire hooks found to remove[/yellow]")

        return

    # Install mode
    if framework == "pre-commit":
        # Generate .pre-commit-config.yaml
        pre_commit_config = Path(".pre-commit-config.yaml")

        if pre_commit_config.exists() and not force:
            console.print(f"[red]Error:[/red] {pre_commit_config} already exists")
            console.print("Use --force to overwrite or manually add TripWire hooks to the file")
            sys.exit(1)

        # Check if pre-commit is installed
        if not shutil.which("pre-commit"):
            console.print("[red]Error:[/red] pre-commit framework not installed")
            console.print("Install it with: [cyan]pip install pre-commit[/cyan]")
            sys.exit(1)

        config_content = """# TripWire Pre-Commit Hooks
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks

repos:
  - repo: local
    hooks:
      - id: tripwire-schema-validate
        name: TripWire Schema Validation
        entry: tripwire schema validate --strict
        language: system
        pass_filenames: false
        always_run: true

      - id: tripwire-secret-scan
        name: TripWire Secret Scan
        entry: tripwire scan --strict
        language: system
        pass_filenames: false
        always_run: true
"""

        pre_commit_config.write_text(config_content)
        console.print(f"[green][OK][/green] Created {pre_commit_config}")

        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  1. Run: [cyan]pre-commit install[/cyan]")
        console.print("  2. Test hooks: [cyan]pre-commit run --all-files[/cyan]")
        console.print("  3. Commit as usual - hooks run automatically")

        return

    # Git hooks mode
    console.print("[bold cyan]Installing TripWire git hooks...[/bold cyan]\n")

    # Create hooks directory if it doesn't exist
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing hook
    if pre_commit_hook.exists() and not force:
        content = pre_commit_hook.read_text()
        if "Generated by TripWire" not in content:
            console.print(f"[red]Error:[/red] {pre_commit_hook} already exists (not managed by TripWire)")
            console.print("Use --force to overwrite, or manually integrate TripWire commands")
            console.print("\nManual integration:")
            console.print("  Add to your existing hook:")
            console.print("  [cyan]tripwire schema validate --strict[/cyan]")
            console.print("  [cyan]tripwire scan --strict[/cyan]")
            sys.exit(1)
        else:
            console.print(f"[yellow][!][/yellow] TripWire hook already installed, updating...")

    # Create config file if it doesn't exist
    if not config_file.exists():
        config_content = """# TripWire Pre-Commit Hook Configuration
# Generated by: tripwire install-hooks

[pre-commit]
enabled = true
strict = true

[checks]
schema_validate = true
secret_scan = true
drift_check = false

[schema_validate]
environment = "development"
strict = true

[secret_scan]
fail_on_critical = true
fail_on_high = false

[drift_check]
# Variables allowed to differ from .env.example
allowed_drift = ["DEBUG", "LOG_LEVEL"]
"""

        config_file.write_text(config_content)
        console.print(f"[green][OK][/green] Created {config_file}")

    # Create pre-commit hook script
    hook_content = f"""#!/bin/bash
# Generated by TripWire - DO NOT EDIT MANUALLY
# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# To disable: git commit --no-verify

CONFIG_FILE=".tripwire-hooks.toml"

# Check if TripWire hooks are enabled
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Warning: TripWire hook configuration not found"
    exit 0
fi

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo "Running TripWire pre-commit checks..."
echo ""

FAILED=0

# Check if schema validation is enabled
if grep -q "schema_validate = true" "$CONFIG_FILE"; then
    if [ -f ".tripwire.toml" ]; then
        echo "Validating .env against schema..."
        if ! tripwire schema validate --strict --environment development; then
            echo "${{RED}}Schema validation failed${{NC}}"
            echo "Fix errors or skip with: git commit --no-verify"
            FAILED=1
        else
            echo "${{GREEN}}Schema validation passed${{NC}}"
        fi
        echo ""
    fi
fi

# Check if secret scan is enabled
if grep -q "secret_scan = true" "$CONFIG_FILE"; then
    echo "Scanning for secrets..."
    if ! tripwire scan --strict --depth 10; then
        echo "${{RED}}Secret scan failed${{NC}}"
        echo "Fix secrets or skip with: git commit --no-verify"
        FAILED=1
    else
        echo "${{GREEN}}No secrets detected${{NC}}"
    fi
    echo ""
fi

# Check if drift check is enabled
if grep -q "drift_check = true" "$CONFIG_FILE"; then
    if [ -f ".env" ] && [ -f ".env.example" ]; then
        echo "Checking for .env drift..."
        if ! tripwire check --strict; then
            echo "${{RED}}Drift check failed${{NC}}"
            echo "Sync with: tripwire sync"
            # Don't fail on drift, just warn
            echo "${{YELLOW}}Warning: .env differs from .env.example${{NC}}"
        else
            echo "${{GREEN}}No drift detected${{NC}}"
        fi
        echo ""
    fi
fi

if [ $FAILED -eq 1 ]; then
    echo "${{RED}}TripWire pre-commit checks failed${{NC}}"
    echo "To skip these checks: git commit --no-verify"
    exit 1
fi

echo "${{GREEN}}All TripWire checks passed${{NC}}"
exit 0
"""

    pre_commit_hook.write_text(hook_content)

    # Make hook executable
    current_perms = pre_commit_hook.stat().st_mode
    pre_commit_hook.chmod(current_perms | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    console.print(f"[green][OK][/green] Created {pre_commit_hook}")
    console.print(f"[green][OK][/green] Made hook executable")

    console.print("\n[bold green]Hooks installed successfully![/bold green]\n")
    console.print("[bold cyan]What happens now:[/bold cyan]")
    console.print("  - Every commit will automatically:")
    console.print("    1. Validate .env against schema (if .tripwire.toml exists)")
    console.print("    2. Scan for secrets in staged files")
    console.print("    3. Optionally check for .env drift\n")

    console.print("[bold cyan]Configuration:[/bold cyan]")
    console.print(f"  - Edit {config_file} to customize checks")
    console.print("  - Enable/disable individual checks")
    console.print("  - Configure strictness levels\n")

    console.print("[bold cyan]To bypass hooks:[/bold cyan]")
    console.print("  git commit --no-verify")


@main.command()
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
    from pathlib import Path

    from rich.table import Table

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
            import json

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


if __name__ == "__main__":
    main()
