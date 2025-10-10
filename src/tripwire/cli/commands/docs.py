"""Docs command for TripWire CLI."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from tripwire.cli.formatters.docs import (
    generate_html_docs,
    generate_json_docs,
    generate_markdown_docs,
)
from tripwire.cli.utils.console import console


@click.command()
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
def docs(format: str, output: str | Path | None) -> None:
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
            # Use standard print for non-markdown output to avoid rich formatting
            import builtins

            builtins.print(doc_content)


__all__ = ["docs"]
