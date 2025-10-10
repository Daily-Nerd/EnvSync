"""Init command for TripWire CLI.

Initializes TripWire in a project by creating .env, .env.example, and
updating .gitignore with project-specific starter variables.
"""

import fnmatch
import secrets
from pathlib import Path

import click

from tripwire.branding import LOGO_BANNER
from tripwire.cli.templates import PROJECT_TEMPLATES
from tripwire.cli.utils.console import console


@click.command()
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


__all__ = ["init"]
