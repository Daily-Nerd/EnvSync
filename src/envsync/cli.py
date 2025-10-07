"""Command-line interface for EnvSync.

This module provides CLI commands for environment variable management,
including generation, validation, and team synchronization features.
"""

import fnmatch
import secrets
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.console import Console

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


@click.group()
@click.version_option(version="0.1.0", prog_name="envsync")
def main() -> None:
    """EnvSync - Smart environment variable management for Python.

    Validate environment variables at import time with type safety,
    format validation, and team synchronization.
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
    """Initialize EnvSync in your project.

    Creates .env, .env.example, and updates .gitignore with project-specific
    starter variables based on your project type.
    """
    console.print("\n[bold cyan]Welcome to EnvSync! 🎯[/bold cyan]\n")

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
        example_with_header = f"""# EnvSync Environment Variables Template
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
        line.strip() for line in gitignore_content.splitlines()
        if line.strip() and not line.strip().startswith('#')
    ]
    has_env_entry = any(
        fnmatch.fnmatch('.env', pattern) for pattern in gitignore_lines
    )

    if not has_env_entry:
        with gitignore_path.open("a") as f:
            # Add proper spacing based on whether file exists and has content
            if gitignore_content:
                if not gitignore_content.endswith("\n"):
                    f.write("\n")
                f.write("\n# Environment variables (EnvSync)\n")
            else:
                # New file - no leading newline
                f.write("# Environment variables (EnvSync)\n")

            f.write(".env\n")
            f.write(".env.local\n")
        console.print("[green]✅ Updated .gitignore[/green]")
    else:
        console.print("[yellow]⚠️  .gitignore already contains .env entries[/yellow]")

    # Success message
    console.print("\n[bold green]Setup complete! ✅[/bold green]\n")
    console.print("Next steps:")
    console.print("  1. Edit .env with your configuration values")
    console.print("  2. Import in your code: [cyan]from envsync import env[/cyan]")
    console.print("  3. Use variables: [cyan]API_KEY = env.require('API_KEY')[/cyan]")
    console.print("\nFor help: [cyan]envsync --help[/cyan]\n")


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
    from envsync.scanner import (
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
# Generated by EnvSync
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
            console.print("Run 'envsync generate --force' to update it")
            sys.exit(1)
        return

    # Check if file exists
    if output_path.exists() and not force:
        console.print(
            f"[red]Error:[/red] {output} already exists. Use --force to overwrite."
        )
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

    from envsync.parser import compare_env_files

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
            console.print("  [cyan]envsync sync[/cyan]")

        if strict:
            sys.exit(1)
    else:
        console.print("[green]✓[/green] No drift detected - .env is in sync with .env.example")
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
    from envsync.parser import compare_env_files, merge_env_files, parse_env_file

    env_path = Path(env_file)
    example_path = Path(example)

    # Validate example file exists
    if not example_path.exists():
        console.print(f"[red]Error:[/red] {example} not found")
        sys.exit(1)

    # Compare files
    missing, extra, common = compare_env_files(env_path, example_path)

    if not missing and not extra:
        console.print("[green]✓[/green] Already in sync - no changes needed")
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

    from envsync.secrets import get_severity_color, scan_env_file, scan_git_history

    console.print("[yellow]Scanning for secrets...[/yellow]\n")

    # Scan current .env file
    env_path = Path(".env")
    findings = []

    if env_path.exists():
        console.print("Scanning .env file...")
        env_findings = scan_env_file(env_path)
        findings.extend(env_findings)

        if env_findings:
            console.print(f"[red]Found {len(env_findings)} potential secret(s) in .env[/red]\n")
        else:
            console.print("[green]✓[/green] No secrets found in .env\n")

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
            console.print("[green]✓[/green] No secrets found in git history\n")

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
        console.print("[green]✓[/green] No secrets detected")
        console.print("Your environment files appear secure")


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
    from envsync.scanner import deduplicate_variables, scan_directory

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

    console.print(f"Found {len(unique_vars)} variable(s): {len(required_vars)} required, {len(optional_vars)} optional\n")

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
        console.print(f"[red]Validation failed:[/red] {len(missing)} required variable(s) missing")
        console.print("\nAdd these variables to your .env file")
        sys.exit(1)
    else:
        console.print("[green]✓[/green] All required variables are set")
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
    from envsync.scanner import deduplicate_variables, scan_directory

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
    from envsync.scanner import EnvVarInfo, format_default_value

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

    required_vars = sorted(
        [v for v in variables.values() if v.required], key=lambda v: v.name
    )

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

    optional_vars = sorted(
        [v for v in variables.values() if not v.required], key=lambda v: v.name
    )

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

            lines.append(
                f"| `{var.name}` | {var.var_type} | `{default_str}` | {desc} | {validation_str} |"
            )

    lines.extend(
        [
            "",
            "## Usage",
            "",
            "To use these variables in your Python code:",
            "",
            "```python",
            "from envsync import env",
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
            "*Generated by [EnvSync](https://github.com/yourusername/envsync)*",
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
    from envsync.scanner import format_default_value

    required_vars = sorted(
        [v for v in variables.values() if v.required], key=lambda v: v.name
    )
    optional_vars = sorted(
        [v for v in variables.values() if not v.required], key=lambda v: v.name
    )

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
    <p><em>Generated by <a href="https://github.com/yourusername/envsync">EnvSync</a></em></p>
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
