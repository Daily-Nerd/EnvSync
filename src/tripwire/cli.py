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

console = Console()

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
@click.version_option(version="0.2.0", prog_name="tripwire", message=f"{LOGO_SIMPLE}\nVersion: %(version)s")
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
        console.print("[yellow]⚠️  .env already exists, skipping...[/yellow]")
    else:
        env_path.write_text(get_template(project_type, inject_secret=True))
        console.print("[green]✅ Created .env[/green]")

    # Create .env.example (with placeholder secrets only)
    example_path = Path(".env.example")
    if example_path.exists():
        console.print("[yellow]⚠️  .env.example already exists, skipping...[/yellow]")
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
        console.print("[green]✅ Created .env.example[/green]")

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
        console.print("[green]✅ Updated .gitignore[/green]")
    else:
        console.print("[yellow]⚠️  .gitignore already contains .env entries[/yellow]")

    # Success message
    console.print("\n[bold green]Setup complete! ✅[/bold green]\n")
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
            console.print(f"[red]✗[/red] {output} does not exist")
            sys.exit(1)

        existing_content = output_path.read_text()
        if existing_content.strip() == generated_content.strip():
            console.print("[green]✓[/green] .env.example is up to date")
        else:
            console.print("[red]✗[/red] .env.example is out of date")
            console.print("Run 'tripwire generate --force' to update it")
            sys.exit(1)
        return

    # Check if file exists
    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite.")
        sys.exit(1)

    # Write file
    output_path.write_text(generated_content)
    console.print(f"[green]✓[/green] Generated {output} with {len(unique_vars)} variable(s)")

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

    console.print(f"[green]✓[/green] Synchronized {env_file}")
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

    console.print("\n[bold cyan]📊 Secret Leak Blast Radius[/bold cyan]")
    console.print("═" * 70)
    console.print()

    # Create visual tree
    tree = Tree("🔍 [bold yellow]Repository Secret Exposure[/bold yellow]")

    for secret_match, timeline in results:
        if timeline.total_occurrences == 0:
            continue

        # Determine status symbol
        status_symbol = "🔴" if timeline.is_currently_in_git else "🟡"
        severity_symbol = "🚨" if timeline.severity == "CRITICAL" else "⚠️"

        secret_node = tree.add(
            f"{status_symbol} {severity_symbol} [yellow]{secret_match.variable_name}[/yellow] "
            f"([red]{timeline.total_occurrences} occurrence(s)[/red])"
        )

        # Add branches
        if timeline.branches_affected:
            branches_node = secret_node.add("[cyan]Branches affected:[/cyan]")
            for branch in timeline.branches_affected[:5]:
                # Note: Showing total commits across all branches since we don't track per-branch
                branches_node.add(f"├─ {branch} ([yellow]{len(timeline.commits_affected)} total commits[/yellow])")

        # Add files
        if timeline.files_affected:
            files_node = secret_node.add("[cyan]Files affected:[/cyan]")
            for file_path in timeline.files_affected[:5]:
                files_node.add(f"├─ [red]{file_path}[/red]")

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
        title="📈 Summary",
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
    console.print("═" * 70)
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
            console.print(f"[bold]📅 {date_str}[/bold]")

            # Show commit info
            console.print(f"   Commit: [cyan]{first_occ.commit_hash[:8]}[/cyan] - {first_occ.commit_message[:60]}")
            console.print(f"   Author: [yellow]@{first_occ.author}[/yellow] <{first_occ.author_email}>")

            # Show files
            for occ in occs:
                console.print(f"   📁 [red]{occ.file_path}[/red]:{occ.line_number}")

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
        impact_lines.append("[bold red]⚠️  CRITICAL: Found in PUBLIC repository![/bold red]")

    console.print(
        Panel(
            "\n".join(impact_lines),
            title="🚨 Security Impact",
            border_style="red" if timeline.severity == "CRITICAL" else "yellow",
        )
    )
    console.print()

    # Generate and display remediation steps
    steps = generate_remediation_steps(timeline, secret_name)

    console.print("[bold yellow]🔧 Remediation Steps:[/bold yellow]\n")

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
            console.print(f"   [red]⚠️  {step.warning}[/red]")

        console.print()

    # Final recommendations
    console.print("[bold cyan]💡 Prevention Tips:[/bold cyan]")
    console.print("  • Always add .env files to .gitignore")
    console.print("  • Use environment variable scanning tools")
    console.print("  • Never commit secrets to version control")
    console.print("  • Use a secret manager for production")
    console.print("  • Enable pre-commit hooks to scan for secrets")
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
            console.print("\n[bold cyan]🔍 Auto-detecting secrets in .env file...[/bold cyan]\n")

        env_file = Path.cwd() / ".env"
        if not env_file.exists():
            console.print("[red]Error:[/red] .env file not found in current directory")
            console.print("Run 'tripwire init' to create one, or specify a secret name to audit.")
            sys.exit(1)

        # Scan .env file for secrets
        detected_secrets = scan_env_file(env_file)

        if not detected_secrets:
            status = get_status_icon("valid")
            console.print(f"{status} No secrets detected in .env file")
            console.print("Your environment file appears secure")
            return

        # Display detected secrets summary (only in non-JSON mode)
        if not output_json:
            console.print(f"[yellow]⚠️  Found {len(detected_secrets)} potential secret(s) in .env file[/yellow]\n")

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
        console.print(f"[green]✓[/green] Documentation written to {output}")
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


if __name__ == "__main__":
    main()
