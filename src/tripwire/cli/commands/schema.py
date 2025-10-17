"""Schema commands for TripWire CLI.

Manages environment variable schemas (.tripwire.toml files) with commands for
creation, validation, migration, and documentation generation.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from tripwire.branding import LOGO_BANNER, get_status_icon
from tripwire.cli.commands.generate import (
    _detect_format,
    _infer_type_and_default,
    _is_placeholder,
    _is_secret,
)
from tripwire.cli.formatters.docs import (
    generate_html_docs,
    generate_json_docs,
    generate_markdown_docs,
)
from tripwire.cli.utils.console import console
from tripwire.cli.utils.helpers import should_skip_file_in_hook

# Phase 1 (v0.12.0): Custom validator prefix for deferred validation
CUSTOM_VALIDATOR_PREFIX = "custom:"


@click.group()
def schema() -> None:
    """Manage environment variable schemas (.tripwire.toml).

    Common Workflows:

      New Project:
        tripwire schema new              # Create blank schema
        tripwire schema from-code        # Or generate from code

      Migrate from .env.example:
        tripwire schema from-example     # Convert to schema
        tripwire schema validate         # Verify .env

      Keep .env.example in sync:
        tripwire schema to-example       # Export schema
        git add .env.example             # Commit

    Quick start: tripwire schema quick-start
    """
    pass


@schema.command("new")
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode with prompts",
)
def schema_new(interactive: bool) -> None:
    """Create a new .tripwire.toml schema file.

    Generates a template configuration schema that you can customize
    for your project's environment variables.

    Examples:
        tripwire schema new              # Create blank schema
        tripwire schema new --interactive # Interactive setup
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
    console.print("  3. Run [cyan]tripwire schema to-example[/cyan] to create .env.example from schema")


@schema.command("validate")
@click.option(
    "--env-file",
    type=click.Path(),  # Removed exists=True to handle missing files gracefully
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
    help="Strict mode for pre-commit hooks (skip gitignored files, pass if file missing in CI/CD)",
)
@click.option(
    "--fail-if-missing",
    is_flag=True,
    help="Exit with error if env file doesn't exist (overrides strict mode behavior)",
)
def schema_validate(env_file: str, schema_file: str, environment: str, strict: bool, fail_if_missing: bool) -> None:
    """Validate .env file against schema.

    Checks that all required variables are present and validates
    types, formats, and constraints defined in .tripwire.toml.

    Behavior:
        Local dev: Validates .env if exists, fails with helpful message if missing
        CI/CD (--strict): Passes if .env missing (correctly not committed), validates if present
        Pre-commit: Skips .gitignore'd files, validates committed files only

    Examples:
        tripwire schema validate                    # Local validation
        tripwire schema validate --strict           # Pre-commit/CI mode
        tripwire schema validate --fail-if-missing  # Force failure if missing
    """
    from rich.table import Table

    from tripwire.schema import validate_with_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema new[/cyan] to create one")
        sys.exit(1)

    env_path = Path(env_file)

    # Smart behavior: Handle missing .env file based on context
    if not env_path.exists():
        if strict and not fail_if_missing:
            # CI/CD context: .env correctly not committed - PASS
            console.print(f"[dim]{env_file} not found (expected in CI/CD - not committed to git)[/dim]")
            console.print("[green][OK][/green] Validation passed (no file to validate)")
            console.print("[dim]Note: This is expected in CI/CD where .env is not committed[/dim]")
            return
        elif fail_if_missing:
            # Explicitly requested to fail if missing
            console.print(f"[red]Error:[/red] {env_file} does not exist")
            console.print(f"Create one with: [cyan]tripwire schema to-env --environment {environment}[/cyan]")
            sys.exit(1)
        else:
            # Local dev: Provide helpful guidance
            console.print(f"[yellow]Warning:[/yellow] {env_file} not found")
            console.print("\nTo create a .env file from your schema:")
            console.print(f"  [cyan]tripwire schema to-env --environment {environment}[/cyan]")
            console.print("\nOr copy from template:")
            console.print("  [cyan]cp .env.example .env[/cyan]")
            sys.exit(1)

    # File exists - check if should skip in strict mode (pre-commit hooks)
    if strict and should_skip_file_in_hook(env_path):
        console.print(f"[dim]Skipping {env_file} (in .gitignore - won't be committed)[/dim]")
        console.print("[green][OK][/green] Validation skipped for ignored file")
        return

    # Perform actual validation
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


@schema.command("to-example")
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
@click.option(
    "--check",
    is_flag=True,
    help="Check if output is up to date (CI mode)",
)
def schema_to_example(schema_file: str, output: str, force: bool, check: bool) -> None:
    """Export schema TO .env.example file.

    Creates a .env.example file from your .tripwire.toml schema,
    including descriptions, examples, and validation rules.

    Examples:
        tripwire schema to-example           # Generate .env.example
        tripwire schema to-example --check   # CI mode (verify up-to-date)
    """
    from tripwire.schema import load_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema new[/cyan] to create one")
        sys.exit(1)

    schema = load_schema(schema_path)
    if not schema:
        console.print("[red]Error:[/red] Failed to load schema")
        sys.exit(1)

    env_example_content = schema.generate_env_example()
    output_path = Path(output)

    # Check mode: compare with existing file
    if check:
        console.print("[yellow]Checking if output is up to date...[/yellow]")
        if not output_path.exists():
            console.print(f"[red][X][/red] {output} does not exist")
            sys.exit(1)

        existing_content = output_path.read_text()
        if existing_content.strip() == env_example_content.strip():
            console.print(f"[green][OK][/green] {output} is up to date")
        else:
            console.print(f"[red][X][/red] {output} is out of date")
            console.print(f"Run 'tripwire schema to-example --force' to update it")
            sys.exit(1)
        return

    if output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite")
        sys.exit(1)

    console.print(f"[yellow]Generating .env.example from {schema_file}...[/yellow]\n")

    output_path.write_text(env_example_content)

    console.print(f"[green][OK][/green] Generated {output}")
    console.print(f"  {len(schema.variables)} variable(s) defined")

    console.print("\n[cyan]Next:[/cyan] Run [cyan]tripwire schema validate[/cyan] to verify your .env file")


@schema.command("from-code")
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
    help="Overwrite existing file (merges with existing schema)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without creating file",
)
@click.option(
    "--validate",
    is_flag=True,
    help="Validate schema after generation (requires custom validators to be imported first)",
)
@click.option(
    "--remove-deprecated",
    is_flag=True,
    help="Remove variables from schema that are no longer in code (default: keep them)",
)
@click.option(
    "--exclude-unused",
    is_flag=True,
    help="Exclude dead variables (declared but never used) from schema",
)
def schema_from_code(
    output: str, force: bool, dry_run: bool, validate: bool, remove_deprecated: bool, exclude_unused: bool
) -> None:
    """Create schema FROM Python code analysis.

    Scans Python files for env.require() and env.optional() calls
    and generates a schema file automatically.

    Examples:
        tripwire schema from-code                # Generate schema from code
        tripwire schema from-code --dry-run      # Preview without creating
    """
    from datetime import datetime

    from tripwire.scanner import deduplicate_variables, scan_directory
    from tripwire.schema import (
        TripWireSchema,
        build_source_comments_from_envvarinfo,
        create_schema_backup,
        envvarinfo_to_variableschema,
        load_existing_schema_safe,
        merge_schemas,
        write_schema_to_toml,
    )

    output_path = Path(output)

    # Check if file exists (unless dry-run)
    if not dry_run and output_path.exists() and not force:
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
    console.print(f"Found {len(unique_vars)} unique variable(s) in code")

    # NEW: Exclude unused variables if flag is set
    if exclude_unused:
        console.print("[dim]Analyzing variable usage to exclude dead code...[/dim]")

        try:
            from tripwire.analysis.usage_tracker import UsageAnalyzer

            analyzer = UsageAnalyzer(Path.cwd())
            result = analyzer.analyze()
            dead_var_names = set(result.dead_variables)

            if dead_var_names:
                # Filter out dead variables and track what was actually removed
                original_var_names = set(unique_vars.keys())
                unique_vars = {
                    var_name: var_info for var_name, var_info in unique_vars.items() if var_name not in dead_var_names
                }
                removed = original_var_names - set(unique_vars.keys())  # Actually removed vars
                removed_count = len(removed)

                if removed_count > 0:
                    console.print(f"[yellow]Excluded {removed_count} unused variable(s) from schema[/yellow]")
                    removed_list = sorted(list(removed))  # Sort for consistency
                    if removed_count <= 5:
                        for var_name in removed_list:
                            console.print(f"  [dim]- {var_name}[/dim]")
                    else:
                        for var_name in removed_list[:5]:
                            console.print(f"  [dim]- {var_name}[/dim]")
                        console.print(f"  [dim]... and {removed_count - 5} more[/dim]")
            else:
                console.print("[green]No dead variables found - all declared variables are used[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze usage: {e}[/yellow]")
            console.print("[dim]Proceeding with all variables...[/dim]")

    source_comments = build_source_comments_from_envvarinfo(unique_vars)

    # Convert EnvVarInfo to VariableSchema
    new_variables = {var_name: envvarinfo_to_variableschema(var_info) for var_name, var_info in unique_vars.items()}

    # Count required vs optional
    required_count = sum(1 for v in new_variables.values() if v.required)
    optional_count = len(new_variables) - required_count

    # Check if existing schema exists for merge
    existing_schema = load_existing_schema_safe(output_path)

    if existing_schema:
        # SMART MERGE: Preserve existing schema, add/update variables
        console.print(f"\n[cyan]Existing schema found - merging with code changes...[/cyan]\n")

        merge_result = merge_schemas(existing_schema, new_variables, remove_deprecated=remove_deprecated)

        # Dry-run mode: show merge preview
        if dry_run:
            console.print("[cyan]Preview of merge changes:[/cyan]\n")

            if merge_result.added_variables:
                console.print(f"[green]✓ Added variables ({len(merge_result.added_variables)}):[/green]")
                for var_name in merge_result.added_variables[:10]:  # Show first 10
                    var_info = new_variables[var_name]
                    console.print(
                        f"  + {var_name} ({var_info.type}, {'required' if var_info.required else 'optional'})"
                    )
                if len(merge_result.added_variables) > 10:
                    console.print(f"  ... and {len(merge_result.added_variables) - 10} more")

            if merge_result.updated_variables:
                console.print(f"\n[yellow]✓ Updated variables ({len(merge_result.updated_variables)}):[/yellow]")
                for var_name, changes in merge_result.updated_variables[:10]:
                    console.print(f"  ~ {var_name}: {', '.join(changes)}")
                if len(merge_result.updated_variables) > 10:
                    console.print(f"  ... and {len(merge_result.updated_variables) - 10} more")

            if merge_result.removed_variables:
                if remove_deprecated:
                    console.print(f"\n[red]✓ Removed variables ({len(merge_result.removed_variables)}):[/red]")
                else:
                    console.print(
                        f"\n[dim]✓ Preserved deprecated variables ({len(merge_result.removed_variables)}):[/dim]"
                    )
                for var_name in merge_result.removed_variables[:10]:
                    if remove_deprecated:
                        console.print(f"  - {var_name} (not in code, will be removed)")
                    else:
                        console.print(f"  = {var_name} (not in code, kept in schema)")
                if len(merge_result.removed_variables) > 10:
                    console.print(f"  ... and {len(merge_result.removed_variables) - 10} more")

            if merge_result.preserved_sections:
                console.print(f"\n[dim]✓ Preserved sections:[/dim]")
                for section in merge_result.preserved_sections:
                    console.print(f"  = {section}")

            console.print(
                f"\n[cyan]Total variables in merged schema: {len(merge_result.merged_schema.variables)}[/cyan]"
            )
            console.print(f"\n[cyan]To apply changes, run without --dry-run[/cyan]")
            return

        # Create backup before overwriting
        if output_path.exists():
            try:
                backup_path = create_schema_backup(output_path)
                console.print(f"[dim]Backup created: {backup_path.name}[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not create backup: {e}[/yellow]\n")

        # Write merged schema (with source comments for new/updated variables)
        write_schema_to_toml(merge_result.merged_schema, output_path, source_comments=source_comments)

        # Show merge summary
        status = get_status_icon("valid")
        console.print(f"{status} [green]Updated {output} with smart merge[/green]\n")

        if merge_result.added_variables:
            console.print(f"  [green]+ {len(merge_result.added_variables)} added[/green]")
        if merge_result.updated_variables:
            console.print(f"  [yellow]~ {len(merge_result.updated_variables)} updated[/yellow]")
        if merge_result.removed_variables:
            if remove_deprecated:
                console.print(f"  [red]- {len(merge_result.removed_variables)} removed[/red]")
            else:
                console.print(
                    f"  [dim]= {len(merge_result.removed_variables)} preserved (use --remove-deprecated to remove)[/dim]"
                )
        if merge_result.preserved_sections:
            console.print(f"  [cyan]✓ {len(merge_result.preserved_sections)} section(s) preserved[/cyan]")

        console.print(f"\n  [bold]Total: {len(merge_result.merged_schema.variables)} variable(s) in schema[/bold]")

    else:
        # NO EXISTING SCHEMA: Create new schema from scratch
        console.print(f"\n[cyan]Creating new schema from code...[/cyan]\n")

        # Create new schema with defaults
        new_schema = TripWireSchema(
            project_name="your-project",
            project_version="0.1.0",
            project_description="Generated from code scanning",
            variables=new_variables,
        )

        # Dry-run mode: show preview
        if dry_run:
            console.print("[cyan]Preview of new schema:[/cyan]\n")
            console.print(f"  [yellow]Found {len(new_variables)} variable(s):[/yellow]")
            console.print(f"    - {required_count} required")
            console.print(f"    - {optional_count} optional")
            console.print(f"\n[cyan]To create the file, run without --dry-run[/cyan]")
            return

        # Write new schema (with source comments)
        write_schema_to_toml(new_schema, output_path, source_comments=source_comments)

        status = get_status_icon("valid")
        console.print(f"{status} [green]Created {output} with {len(new_variables)} variable(s)[/green]")
        console.print(f"  - {required_count} required")
        console.print(f"  - {optional_count} optional")

    # Conditionally validate the generated schema
    if validate:
        console.print("\n[yellow]Validating generated schema...[/yellow]")

        try:
            # Call schema_check to validate the generated file
            ctx = click.get_current_context()
            ctx.invoke(schema_check, schema_file=output)
        except Exception as e:
            console.print(f"[red]Schema validation failed:[/red] {e}")
            console.print("\n[cyan]Next:[/cyan]")
            console.print(f"  1. Review {output} and fix validation errors")
            console.print("  2. Run: [cyan]tripwire schema check[/cyan]")
            sys.exit(1)
    else:
        # Schema validation skipped - explain workflow for custom validators
        console.print("\n[dim]Schema validation skipped (use --validate to check after generation)[/dim]")
        console.print("[dim]Note: If using custom validators, import them before running validation:[/dim]")
        console.print("[dim]  1. Ensure custom validators are registered in your code[/dim]")
        console.print("[dim]  2. Import the module: python -c 'import your_module'[/dim]")
        console.print("[dim]  3. Then run: tripwire schema check[/dim]")

    console.print("\n[cyan]Next:[/cyan]")
    console.print(f"  • Review {output} and customize as needed")
    if not validate:
        console.print(f"  • Run [cyan]tripwire schema check[/cyan] to validate schema syntax")
    console.print("  • Run [cyan]tripwire schema validate[/cyan] to check against your .env files")
    console.print("  • Run [cyan]tripwire schema to-example[/cyan] to generate .env.example")


@schema.command("from-example")
@click.option(
    "--source",
    type=click.Path(exists=True),
    default=".env.example",
    help="Source .env.example file to convert",
)
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
    help="Overwrite existing file (merges with existing schema)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without creating file",
)
@click.option(
    "--remove-deprecated",
    is_flag=True,
    help="Remove variables from schema that are not in .env.example (default: keep them)",
)
def schema_from_example(source: str, output: str, force: bool, dry_run: bool, remove_deprecated: bool) -> None:
    """Create schema FROM .env.example file.

    Converts .env.example placeholders to .tripwire.toml schema
    definitions with type inference and validation rules.

    Examples:
        tripwire schema from-example                 # Convert .env.example
        tripwire schema from-example --dry-run       # Preview first
        tripwire schema from-example --source .env.template
    """
    import tomli_w

    source_path = Path(source)
    output_path = Path(output)

    # Check if source exists
    if not source_path.exists():
        console.print(f"[red]Error:[/red] Source file {source} does not exist")
        console.print("[yellow]Tip:[/yellow] Use --source to specify a different file")
        sys.exit(1)

    # Security check: Warn if migrating from .env (not .env.example)
    is_real_env = source_path.name == ".env" or (
        source_path.name.startswith(".env.") and not source_path.name.endswith(".example")
    )

    if is_real_env:
        console.print("[bold red]WARNING: Source file appears to be a real environment file![/bold red]")
        console.print()
        console.print(".env files contain real secrets that should NOT be in schema defaults.")
        console.print("Schema files (.tripwire.toml) are meant to be committed to git.")
        console.print()
        console.print("[yellow]Recommendation:[/yellow] Create .env.example first with placeholder values:")
        console.print("  1. Copy .env to .env.example: [cyan]cp .env .env.example[/cyan]")
        console.print("  2. Replace secret values with placeholders (e.g., 'your-api-key-here')")
        console.print("  3. Run: [cyan]tripwire schema from-example[/cyan]")
        console.print()
        console.print("[yellow]Alternative:[/yellow] Use [cyan]tripwire schema from-code[/cyan] to scan code instead")
        console.print()
        console.print("[bold yellow]Secret values will be excluded from schema for security.[/bold yellow]")
        console.print()

        if not click.confirm("Continue anyway?", default=False):
            console.print("[yellow]Migration cancelled[/yellow]")
            sys.exit(0)

    # Check if output exists (unless dry-run)
    if not dry_run and output_path.exists() and not force:
        console.print(f"[red]Error:[/red] {output} already exists. Use --force to overwrite.")
        sys.exit(1)

    console.print(f"[yellow]Converting {source} to {output}...[/yellow]")

    # Parse .env.example file
    env_vars: dict[str, dict[str, Any]] = {}
    pending_comment: str | None = None

    try:
        with open(source_path) as f:
            for line in f:
                line_stripped = line.strip()

                if not line_stripped:
                    continue

                # Handle comments
                if line_stripped.startswith("#"):
                    comment_text = line_stripped[1:].strip()

                    if not comment_text or comment_text.startswith("="):
                        continue

                    # Detect section headers
                    is_section_header = (
                        len(comment_text.split()) <= 4
                        and not any(c in comment_text for c in [",", ":", ";", "."])
                        and comment_text[0].isupper()
                    )

                    if not is_section_header:
                        pending_comment = comment_text
                    continue

                # Handle variable declarations
                if "=" in line_stripped:
                    parts = line_stripped.split("=", 1)
                    var_name = parts[0].strip()
                    value = parts[1].strip() if len(parts) > 1 else ""

                    current_var = {
                        "type": "string",
                        "required": True,
                        "description": pending_comment or "",
                    }

                    pending_comment = None

                    # Type inference from value
                    if value:
                        current_var["type"], current_var["default"] = _infer_type_and_default(value)

                        if _is_placeholder(value):
                            current_var.pop("default", None)
                            current_var["required"] = True

                        # Detect format validators
                        format_type = _detect_format(var_name, value)
                        if format_type:
                            current_var["format"] = format_type

                        # Detect secrets
                        if _is_secret(var_name, value):
                            current_var["secret"] = True

                    else:
                        current_var["required"] = True

                    env_vars[var_name] = current_var

    except Exception as e:
        console.print(f"[red]Error reading {source}:[/red] {e}")
        sys.exit(1)

    if not env_vars:
        console.print("[yellow]No variables found in source file[/yellow]")
        sys.exit(1)

    from tripwire.schema import (
        TripWireSchema,
        VariableSchema,
        create_schema_backup,
        load_existing_schema_safe,
        merge_schemas,
        write_schema_to_toml,
    )

    # Convert parsed env_vars dict to VariableSchema objects
    new_variables: dict[str, VariableSchema] = {}
    for var_name, var_data in env_vars.items():
        # Security: Never include defaults for secrets in schema (v0.7.1)
        default_value = None
        if "default" in var_data and not var_data.get("secret", False):
            default_value = var_data["default"]

        new_variables[var_name] = VariableSchema(
            name=var_name,
            type=var_data["type"],
            required=var_data.get("required", False),
            default=default_value,
            description=var_data.get("description", ""),
            secret=var_data.get("secret", False),
            format=var_data.get("format"),
        )

    # Count statistics
    required_count = sum(1 for v in new_variables.values() if v.required)
    optional_count = len(new_variables) - required_count
    secret_count = sum(1 for v in new_variables.values() if v.secret)

    # Check if existing schema exists for merge
    existing_schema = load_existing_schema_safe(output_path)

    if existing_schema:
        # SMART MERGE: Preserve existing schema, add/update variables
        console.print(f"\n[cyan]Existing schema found - merging with .env.example changes...[/cyan]\n")

        merge_result = merge_schemas(existing_schema, new_variables, remove_deprecated=remove_deprecated)

        # Dry-run mode: show merge preview
        if dry_run:
            console.print("[cyan]Preview of merge changes:[/cyan]\n")

            if merge_result.added_variables:
                console.print(f"[green]✓ Added variables ({len(merge_result.added_variables)}):[/green]")
                for var_name in merge_result.added_variables[:10]:
                    var_info = new_variables[var_name]
                    console.print(
                        f"  + {var_name} ({var_info.type}, {'required' if var_info.required else 'optional'})"
                    )
                if len(merge_result.added_variables) > 10:
                    console.print(f"  ... and {len(merge_result.added_variables) - 10} more")

            if merge_result.updated_variables:
                console.print(f"\n[yellow]✓ Updated variables ({len(merge_result.updated_variables)}):[/yellow]")
                for var_name, changes in merge_result.updated_variables[:10]:
                    console.print(f"  ~ {var_name}: {', '.join(changes)}")
                if len(merge_result.updated_variables) > 10:
                    console.print(f"  ... and {len(merge_result.updated_variables) - 10} more")

            if merge_result.removed_variables:
                if remove_deprecated:
                    console.print(f"\n[red]✓ Removed variables ({len(merge_result.removed_variables)}):[/red]")
                else:
                    console.print(
                        f"\n[dim]✓ Preserved deprecated variables ({len(merge_result.removed_variables)}):[/dim]"
                    )
                for var_name in merge_result.removed_variables[:10]:
                    if remove_deprecated:
                        console.print(f"  - {var_name} (not in .env.example, will be removed)")
                    else:
                        console.print(f"  = {var_name} (not in .env.example, kept in schema)")
                if len(merge_result.removed_variables) > 10:
                    console.print(f"  ... and {len(merge_result.removed_variables) - 10} more")

            if merge_result.preserved_sections:
                console.print(f"\n[dim]✓ Preserved sections:[/dim]")
                for section in merge_result.preserved_sections:
                    console.print(f"  = {section}")

            console.print(
                f"\n[cyan]Total variables in merged schema: {len(merge_result.merged_schema.variables)}[/cyan]"
            )
            console.print(f"\n[cyan]To apply changes, run without --dry-run[/cyan]")
            return

        # Create backup before overwriting
        if output_path.exists():
            try:
                backup_path = create_schema_backup(output_path)
                console.print(f"[dim]Backup created: {backup_path.name}[/dim]\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not create backup: {e}[/yellow]\n")

        # Write merged schema
        write_schema_to_toml(merge_result.merged_schema, output_path)

        # Show merge summary
        status = get_status_icon("valid")
        console.print(f"{status} [green]Updated {output} with smart merge[/green]\n")

        if merge_result.added_variables:
            console.print(f"  [green]+ {len(merge_result.added_variables)} added[/green]")
        if merge_result.updated_variables:
            console.print(f"  [yellow]~ {len(merge_result.updated_variables)} updated[/yellow]")
        if merge_result.removed_variables:
            if remove_deprecated:
                console.print(f"  [red]- {len(merge_result.removed_variables)} removed[/red]")
            else:
                console.print(
                    f"  [dim]= {len(merge_result.removed_variables)} preserved (use --remove-deprecated to remove)[/dim]"
                )
        if merge_result.preserved_sections:
            console.print(f"  [cyan]✓ {len(merge_result.preserved_sections)} section(s) preserved[/cyan]")

        console.print(f"\n  [bold]Total: {len(merge_result.merged_schema.variables)} variable(s) in schema[/bold]")

    else:
        # NO EXISTING SCHEMA: Create new schema from scratch
        console.print(f"\n[cyan]Creating new schema from .env.example...[/cyan]\n")

        # Create new schema with defaults
        new_schema = TripWireSchema(
            project_name=Path.cwd().name,
            project_version="0.1.0",
            project_description="Environment variable schema",
            variables=new_variables,
        )

        # Dry-run mode: show preview
        if dry_run:
            console.print(f"[cyan]Preview of schema from {source}:[/cyan]\n")
            console.print(f"[yellow]Found {len(new_variables)} variable(s):[/yellow]")
            if required_count:
                console.print(f"  - {required_count} required")
            if optional_count:
                console.print(f"  - {optional_count} optional")
            if secret_count:
                console.print(f"  - {secret_count} secret(s) detected")

            console.print(f"\n[cyan]Inferred types:[/cyan]")
            for var_name, var_schema in list(new_variables.items())[:5]:
                has_default = var_schema.default is not None
                console.print(f"  • {var_name}: {var_schema.type}" + (" (with default)" if has_default else ""))
            if len(new_variables) > 5:
                console.print(f"  ... and {len(new_variables) - 5} more")

            console.print(f"\n[cyan]To create {output}, run without --dry-run[/cyan]")
            return

        # Write new schema
        try:
            write_schema_to_toml(new_schema, output_path)

            status = get_status_icon("valid")
            console.print(f"{status} [green]Created {output} with {len(new_variables)} variable(s)[/green]")

            if required_count:
                console.print(f"  - {required_count} required")
            if optional_count:
                console.print(f"  - {optional_count} optional")
            if secret_count:
                console.print(f"  - {secret_count} secret(s)")
                console.print("  [dim](secrets have no defaults for security)[/dim]")

        except Exception as e:
            console.print(f"[red]Error writing {output}:[/red] {e}")
            sys.exit(1)

    console.print("\n[cyan]Next:[/cyan]")
    console.print(f"  • Review {output} and adjust types/validation rules")
    console.print("  • Run [cyan]tripwire schema validate[/cyan] to check your .env")
    console.print("  • Run [cyan]tripwire schema to-env[/cyan] to generate .env from schema")


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
        console.print("Run [cyan]tripwire schema new[/cyan] to create one")
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

    # Check 3: Format validators (include custom validators from registry)
    from tripwire.validation import list_validators

    # Get all registered validators (builtin + custom)
    all_validators = list_validators()
    valid_formats = set(all_validators.keys())
    format_errors = []
    format_warnings = []  # Phase 1 (v0.12.0): Track custom validators separately

    if "variables" in data:
        for var_name, var_config in data["variables"].items():
            if "format" in var_config:
                fmt = var_config["format"]

                # Phase 1 (v0.12.0): Handle custom: prefix
                if fmt.startswith(CUSTOM_VALIDATOR_PREFIX):
                    custom_name = fmt[len(CUSTOM_VALIDATOR_PREFIX) :]  # Strip prefix
                    format_warnings.append(
                        f"variables.{var_name}: Uses custom validator '{custom_name}' "
                        f"(validation deferred to runtime - ensure validator is registered at import-time)"
                    )
                    continue  # Skip further validation for custom validators

                if fmt not in valid_formats:
                    # Provide helpful error message suggesting registration or custom: prefix
                    builtin_validators = {name for name, vtype in all_validators.items() if vtype == "built-in"}
                    format_errors.append(
                        f"variables.{var_name}: Unknown format '{fmt}'. "
                        f"Builtin formats: {', '.join(sorted(builtin_validators))}. "
                        f"To use custom validators, use format = '{CUSTOM_VALIDATOR_PREFIX}{fmt}' in schema"
                    )

    if not format_errors:
        status = get_status_icon("valid")
        # Show count of custom validators if any
        custom_count = sum(1 for vtype in all_validators.values() if vtype == "custom")
        validator_msg = "All format validators exist"
        if custom_count > 0:
            validator_msg += (
                f" ({len(valid_formats)} total: {len(valid_formats) - custom_count} builtin, {custom_count} custom)"
            )
        console.print(f"{status} {validator_msg}")
    else:
        status = get_status_icon("invalid")
        console.print(f"{status} Format validator issues found")
        errors.extend(format_errors)

    # Phase 1 (v0.12.0): Show warnings for custom validators (non-blocking)
    if format_warnings:
        console.print()
        console.print("[yellow]Custom validators detected (runtime validation only):[/yellow]")
        for warning in format_warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

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

    # Check 7: Security - secrets should not have defaults (v0.7.1)
    if "variables" in data:
        for var_name, var_config in data["variables"].items():
            if var_config.get("secret") and "default" in var_config:
                warnings.append(f"variables.{var_name}: Secret has default value (security risk - remove default)")

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


@schema.command("to-env")
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
    default=False,
    help="Validate after generation (custom validators must be imported first)",
)
@click.option(
    "--format-output",
    type=click.Choice(["env", "json", "yaml"]),
    default="env",
    help="Output format",
)
def schema_to_env(
    environment: str,
    output: Optional[str],
    schema_file: str,
    interactive: bool,
    overwrite: bool,
    validate: bool,
    format_output: str,
) -> None:
    """Export schema TO .env file.

    Creates a .env file for a specific environment using defaults
    from .tripwire.toml. Optionally prompts for secret values.

    Examples:
        tripwire schema to-env --environment production
        tripwire schema to-env -e staging -i         # Interactive mode
        tripwire schema to-env -e prod --output /tmp/.env.prod
    """
    import json

    from tripwire.schema import load_schema, validate_with_schema

    schema_path = Path(schema_file)
    if not schema_path.exists():
        console.print(f"[red]Error:[/red] Schema file not found: {schema_file}")
        console.print("Run [cyan]tripwire schema new[/cyan] to create one")
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

    # Check if schema has variables defined
    if not schema.variables:
        console.print("[yellow][!]  No variables defined in .tripwire.toml yet[/yellow]")
        console.print()
        console.print("[bold]To get started:[/bold]")
        console.print("  1. Edit .tripwire.toml and uncomment example variables, or")
        console.print("  2. Add your own variable definitions, or")
        console.print("  3. Import from code: [cyan]tripwire schema from-code[/cyan]")
        console.print()
        console.print("[bold]Example variable definition:[/bold]")
        console.print()
        console.print("[cyan][variables.DATABASE_URL]")
        console.print('type = "string"')
        console.print("required = true")
        console.print('format = "postgresql"')
        console.print('description = "Database connection URL"[/cyan]')
        console.print()
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

    # Validate after generation (opt-in)
    if validate and format_output == "env":
        console.print(f"\n[yellow]Validating generated file...[/yellow]")
        console.print("[dim]Note: Custom validators must be imported before validation[/dim]")

        is_valid, errors = validate_with_schema(output_path, schema_path, environment)

        if is_valid:
            status = get_status_icon("valid")
            console.print(f"{status} [green]Validation passed![/green]")
        else:
            status = get_status_icon("invalid")
            console.print(f"{status} [red]Validation failed:[/red]")
            console.print("[dim]Tip: Import custom validators before running this command[/dim]")
            console.print("[dim]Example: python -c 'import your_module' && tripwire schema to-env --validate[/dim]")
            for error in errors:
                console.print(f"  - [red]{error}[/red]")
    elif format_output == "env":
        # Validation skipped - provide workflow guidance
        console.print("\n[dim]Validation skipped (use --validate to check generated file)[/dim]")
        console.print("[dim]Note: For custom validators, import them before validation[/dim]")

    console.print("\n[bold cyan]Next steps:[/bold cyan]")
    console.print(f"  1. Review {output} and fill in any missing values")
    if format_output == "env" and not validate:
        console.print(
            f"  2. Validate: [cyan]tripwire schema validate --env-file {output} --environment {environment}[/cyan]"
        )
    elif format_output == "env":
        console.print(
            f"  2. Re-validate if needed: [cyan]tripwire schema validate --env-file {output} --environment {environment}[/cyan]"
        )


@schema.command("to-docs")
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
def schema_to_docs(schema_file: str, format: str, output: Optional[str]) -> None:
    """Export schema TO documentation.

    Creates comprehensive documentation for your environment variables
    based on the schema definitions in .tripwire.toml.

    Examples:
        tripwire schema to-docs                    # Output to stdout
        tripwire schema to-docs --output ENV.md    # Save to file
        tripwire schema to-docs --format html      # HTML output
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
                    "required": c.new_schema.required if c.new_schema else False,
                    "type": c.new_schema.type if c.new_schema else "unknown",
                    "breaking": c.breaking,
                }
                for c in diff.added_variables
            ],
            "removed": [
                {
                    "variable": c.variable_name,
                    "was_required": c.old_schema.required if c.old_schema else False,
                    "type": c.old_schema.type if c.old_schema else "unknown",
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
                schema_type = change.new_schema.type if change.new_schema else "unknown"
                schema_required = change.new_schema.required if change.new_schema else False
                lines.append(
                    f"| `{change.variable_name}` | {schema_type} | "
                    f"{'Yes' if schema_required else 'No'} | "
                    f"{'Yes' if change.breaking else 'No'} |"
                )
            lines.append("")

        if diff.removed_variables:
            lines.append("## Removed Variables")
            lines.append("")
            lines.append("| Variable | Type | Was Required | Breaking |")
            lines.append("|----------|------|--------------|----------|")
            for change in diff.removed_variables:
                schema_type = change.old_schema.type if change.old_schema else "unknown"
                schema_required = change.old_schema.required if change.old_schema else False
                lines.append(
                    f"| `{change.variable_name}` | {schema_type} | "
                    f"{'Yes' if schema_required else 'No'} | "
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
            schema_type = change.new_schema.type if change.new_schema else "unknown"
            schema_required = change.new_schema.required if change.new_schema else False
            schema_desc = change.new_schema.description if change.new_schema else "-"
            table.add_row(
                change.variable_name,
                schema_type,
                "Yes" if schema_required else "No",
                schema_desc or "-",
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
            schema_type = change.old_schema.type if change.old_schema else "unknown"
            schema_required = change.old_schema.required if change.old_schema else False
            schema_desc = change.old_schema.description if change.old_schema else "-"
            table.add_row(
                change.variable_name,
                schema_type,
                "Yes" if schema_required else "No",
                schema_desc or "-",
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
        console.print(f"  Run: [cyan]tripwire schema upgrade --from {schema1} --to {schema2}[/cyan]")


@schema.command("upgrade")
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
def schema_upgrade(
    from_schema: str,
    to_schema: str,
    env_file: str,
    dry_run: bool,
    interactive: bool,
    force: bool,
    backup: bool,
) -> None:
    """Upgrade .env between schema versions.

    Updates .env file to match new schema, adding missing variables,
    removing deprecated ones, and converting types where possible.

    Examples:
        tripwire schema upgrade --from old.toml --to new.toml
        tripwire schema upgrade --from old.toml --to new.toml --dry-run
        tripwire schema upgrade --from old.toml --to new.toml --force
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
            if change.new_schema and change.new_schema.default is not None:
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
    success, messages = plan.execute(dry_run=False, interactive=interactive, create_backup=backup)

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


@schema.command("quick-start")
@click.option(
    "--source",
    type=click.Choice(["code", "example"]),
    default="code",
    help="Generate from code or .env.example",
)
def schema_quick_start(source: str) -> None:
    """Quick setup wizard for schema-based workflow.

    Runs complete workflow:
      1. Create schema (from code or .env.example)
      2. Validate schema syntax
      3. Generate .env.example from schema
      4. Validate .env against schema (if exists)

    Examples:
        tripwire schema quick-start                  # From code
        tripwire schema quick-start --source example # From .env.example
    """
    ctx = click.get_current_context()

    console.print("[bold cyan]TripWire Schema Quick Start[/bold cyan]\n")

    # Step 1: Create schema
    if source == "code":
        console.print("[1/4] Creating schema from Python code...")
        try:
            ctx.invoke(schema_from_code, output=".tripwire.toml", force=True, dry_run=False)
        except SystemExit as e:
            if e.code != 0:
                console.print("[red]Failed to create schema[/red]")
                sys.exit(1)
    else:
        console.print("[1/4] Creating schema from .env.example...")
        try:
            ctx.invoke(schema_from_example, source=".env.example", output=".tripwire.toml", force=True, dry_run=False)
        except SystemExit as e:
            if e.code != 0:
                console.print("[red]Failed to create schema[/red]")
                sys.exit(1)

    # Step 2: Validate schema syntax
    console.print("\n[2/4] Validating schema syntax...")
    try:
        ctx.invoke(schema_check, schema_file=".tripwire.toml")
    except SystemExit as e:
        if e.code != 0:
            console.print("[red]Schema validation failed[/red]")
            sys.exit(1)

    # Step 3: Generate .env.example
    console.print("\n[3/4] Generating .env.example from schema...")
    try:
        ctx.invoke(schema_to_example, output=".env.example", schema_file=".tripwire.toml", force=True, check=False)
    except SystemExit as e:
        if e.code != 0:
            console.print("[red]Failed to generate .env.example[/red]")
            sys.exit(1)

    # Step 4: Validate .env (if exists)
    if Path(".env").exists():
        console.print("\n[4/4] Validating .env against schema...")
        try:
            ctx.invoke(
                schema_validate, env_file=".env", schema_file=".tripwire.toml", environment="development", strict=False
            )
        except SystemExit as e:
            if e.code != 0:
                console.print("[yellow].env validation failed (non-critical)[/yellow]")
    else:
        console.print("\n[4/4] Skipping .env validation (file doesn't exist)")

    console.print("\n[green]Schema setup complete![/green]")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("  • Review and customize .tripwire.toml")
    console.print("  • Run [cyan]tripwire schema validate[/cyan] in CI")
    console.print("  • Keep .env.example in sync with [cyan]tripwire schema to-example[/cyan]")


__all__ = ["schema"]
