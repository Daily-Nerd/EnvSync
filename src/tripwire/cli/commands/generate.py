"""Generate command for TripWire CLI.

Generates .env.example from Python code or schema files by scanning for
environment variable usage.
"""

import re
import sys
from pathlib import Path
from typing import Any

import click

from tripwire.cli.utils.console import console


def _infer_type_and_default(value: str) -> tuple[str, Any]:
    """Infer type and default value from string with intelligent boolean detection.

    Boolean patterns recognized (v0.7.1+):
    - true/false
    - yes/no
    - on/off
    - enabled/disabled
    - 1/0 (when clearly used as boolean)

    Args:
        value: String value from .env.example

    Returns:
        Tuple of (type_name, default_value)
    """
    value_lower = value.lower().strip()

    # Comprehensive boolean detection (v0.7.1 fix)
    # Check BEFORE numeric parsing to catch "0" and "1" as booleans
    boolean_true_values = {"true", "yes", "on", "enabled", "1"}
    boolean_false_values = {"false", "no", "off", "disabled", "0"}

    if value_lower in boolean_true_values:
        return "bool", True
    elif value_lower in boolean_false_values:
        return "bool", False

    # Try integer (after boolean check)
    try:
        int_val = int(value)
        return "int", int_val
    except ValueError:
        pass

    # Try float
    try:
        float_val = float(value)
        return "float", float_val
    except ValueError:
        pass

    # Default to string
    return "string", value


def _is_placeholder(value: str) -> bool:
    """Check if value is a placeholder."""
    placeholder_patterns = [
        r"your-.*-here",
        r"change.?me",
        r"replace.?me",
        r"example",
        r"placeholder",
        r"<.*>",
        r"\[.*\]",
        r"xxx+",
    ]

    value_lower = value.lower()
    return any(re.search(pattern, value_lower) for pattern in placeholder_patterns)


def _detect_format(var_name: str, value: str) -> str | None:
    """Detect format validator based on variable name and value."""
    name_lower = var_name.lower()

    # PostgreSQL URL
    if "postgresql://" in value or "postgres://" in value:
        return "postgresql"

    # URL
    if value.startswith(("http://", "https://", "ftp://")):
        return "url"

    # Email
    if "email" in name_lower and "@" in value:
        return "email"

    # UUID
    if "uuid" in name_lower or "guid" in name_lower:
        return "uuid"

    # IPv4
    if "ip" in name_lower and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return "ipv4"

    return None


def _is_secret(var_name: str, value: str) -> bool:
    """Detect if variable is likely a secret using comprehensive detection.

    Uses the same secret detection engine as 'audit --all' command for consistency.
    Detects secrets via:
    - 45+ platform-specific patterns (AWS, GitHub, Stripe, etc.)
    - Generic credential detection with entropy analysis
    - High-entropy string detection
    - Placeholder filtering to avoid false positives

    Args:
        var_name: Environment variable name
        value: Environment variable value

    Returns:
        True if variable appears to be a secret
    """
    from tripwire.secrets import detect_secrets_in_value

    # Use comprehensive secret detection from secrets.py
    # This ensures consistency with 'audit --all' command
    matches = detect_secrets_in_value(var_name, value, line_number=0)

    return len(matches) > 0


def _generate_from_schema(output: str, check: bool, force: bool, schema_file: str) -> None:
    """Generate .env.example from .tripwire.toml schema."""
    from tripwire.schema import load_schema

    schema_path = Path(schema_file)

    # Check if schema file exists
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file {schema_file} does not exist")
        console.print(f"[yellow]Tip:[/yellow] Create one with: tripwire schema new")
        sys.exit(1)

    console.print(f"[yellow]Generating from {schema_file}...[/yellow]")

    # Load schema
    try:
        schema = load_schema(schema_path)
        if schema is None:
            console.print(f"[red]Error:[/red] Failed to load schema from {schema_file}")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error loading schema:[/red] {e}")
        sys.exit(1)

    # Generate .env.example content from schema
    try:
        generated_content = schema.generate_env_example()
    except Exception as e:
        console.print(f"[red]Error generating content:[/red] {e}")
        sys.exit(1)

    output_path = Path(output)

    # Check mode: compare with existing file
    if check:
        console.print("[yellow]Checking if output is up to date...[/yellow]")
        if not output_path.exists():
            console.print(f"[red][X][/red] {output} does not exist")
            sys.exit(1)

        existing_content = output_path.read_text()
        if existing_content.strip() == generated_content.strip():
            console.print(f"[green][OK][/green] {output} is up to date")
        else:
            console.print(f"[red][X][/red] {output} is out of date")
            console.print(f"Run 'tripwire generate --from-schema --force' to update it")
            sys.exit(1)
        return

    # Check if file exists
    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite.")
        sys.exit(1)

    # Write file
    try:
        output_path.write_text(generated_content)
        var_count = len(schema.variables)
        console.print(f"[green][OK][/green] Generated {output} with {var_count} variable(s)")

        # Show breakdown
        required_count = sum(1 for v in schema.variables.values() if v.required)
        optional_count = var_count - required_count

        if required_count:
            console.print(f"  - {required_count} required")
        if optional_count:
            console.print(f"  - {optional_count} optional")

    except Exception as e:
        console.print(f"[red]Error writing {output}:[/red] {e}")
        sys.exit(1)


@click.command()
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
def generate(output: str | Path, check: bool, force: bool) -> None:
    """Generate .env.example from Python code.

    Scans your Python code for env.require() and env.optional() calls
    and generates a documented .env.example file.

    Examples:
        tripwire generate                    # Generate .env.example
        tripwire generate --check            # CI mode (verify up-to-date)
        tripwire generate --force            # Overwrite existing file
    """
    # Use code-based generation
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

    console.print(
        "\n[cyan]Next:[/cyan] For more control and type validation, use [cyan]tripwire schema from-code[/cyan]"
    )


__all__ = [
    "generate",
    "_infer_type_and_default",
    "_is_placeholder",
    "_detect_format",
    "_is_secret",
    "_generate_from_schema",
]
