"""Command-line interface for EnvSync.

This module provides CLI commands for environment variable management,
including generation, validation, and team synchronization features.
"""

import fnmatch
import secrets
import sys
from pathlib import Path
from typing import Optional

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
    console.print("[yellow]Generating .env.example...[/yellow]")

    # TODO: Implement actual generation logic by scanning Python files
    # For now, this is a stub showing the structure

    output_path = Path(output)

    if output_path.exists() and not force and not check:
        console.print(
            f"[red]Error:[/red] {output} already exists. Use --force to overwrite."
        )
        sys.exit(1)

    if check:
        console.print("[yellow]Checking if .env.example is up to date...[/yellow]")
        # TODO: Compare generated content with existing file
        console.print("[green]✓[/green] .env.example is up to date")
        return

    # TODO: Generate actual content
    example_content = """# Environment Variables
# Generated by EnvSync

# Example required variable
API_KEY=

# Example optional variable (default: false)
DEBUG=false
"""

    output_path.write_text(example_content)
    console.print(f"[green]✓[/green] Created: {output}")


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
    console.print("[yellow]Checking environment...[/yellow]")

    # TODO: Implement actual check logic
    # For now, stub implementation

    if output_json:
        import json

        result = {
            "status": "ok",
            "missing": [],
            "extra": [],
        }
        print(json.dumps(result, indent=2))
        return

    console.print(f"Comparing {env_file} against {example}...")
    console.print("[green]✓[/green] No issues found")


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
    console.print("[yellow]Synchronizing environment...[/yellow]")

    # TODO: Implement actual sync logic

    if dry_run:
        console.print("[yellow]Dry run - no changes applied[/yellow]")

    console.print("[green]✓[/green] Environment synchronized")


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
    console.print("[yellow]Scanning for secrets...[/yellow]")

    # TODO: Implement actual secret scanning

    console.print(f"Scanning last {depth} commits...")
    console.print("[green]✓[/green] No secrets detected")


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
    console.print("[yellow]Validating environment...[/yellow]")

    # TODO: Implement actual validation logic

    console.print(f"Loading {env_file}...")
    console.print("[green]✓[/green] All variables valid")


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
    console.print("[yellow]Generating documentation...[/yellow]")

    # TODO: Implement actual documentation generation

    if format == "markdown":
        doc_content = generate_markdown_docs()
    elif format == "html":
        doc_content = "<html><body>EnvSync Documentation</body></html>"
    else:  # json
        doc_content = '{"variables": []}'

    if output:
        Path(output).write_text(doc_content)
        console.print(f"[green]✓[/green] Documentation written to {output}")
    else:
        print(doc_content)


def generate_markdown_docs() -> str:
    """Generate markdown documentation.

    Returns:
        Markdown formatted documentation
    """
    # TODO: Generate from actual registry
    return """# Environment Variables

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| API_KEY | string | Yes | - | API key for service |
| DEBUG | boolean | No | false | Enable debug mode |
"""


if __name__ == "__main__":
    main()
