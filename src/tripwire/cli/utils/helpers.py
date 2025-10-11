"""Helper functions for TripWire CLI."""

import subprocess
from pathlib import Path
from typing import Any

import click

from tripwire.branding import LOGO_BANNER
from tripwire.cli.utils.console import console


def print_help_with_banner(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    """Show banner before help text.

    Args:
        ctx: Click context
        _param: Parameter that triggered callback
        value: Parameter value
    """
    if value and not ctx.resilient_parsing:
        console.print(f"[cyan]{LOGO_BANNER}[/cyan]")
        console.print(ctx.get_help())
        ctx.exit()


def is_file_in_gitignore(file_path: Path) -> bool:
    """Check if a file is in .gitignore using git check-ignore.

    This function uses git's native check-ignore to determine if a file
    would be ignored by git. This respects both .gitignore files and
    git's global ignore configuration.

    Args:
        file_path: Path to the file to check

    Returns:
        True if file is in .gitignore, False otherwise
    """
    if not file_path.exists():
        return False

    # Check if we're in a git repository
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=file_path.parent if file_path.is_file() else file_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not in a git repository or git not available
        return False

    # Use git check-ignore to determine if file is ignored
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(file_path)],
            capture_output=True,
            text=True,
        )
        # Exit code 0 means file is ignored
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Error running git check-ignore
        return False


def should_skip_file_in_hook(file_path: Path) -> bool:
    """Determine if a file should be skipped in pre-commit hook context.

    Files should be skipped if they are in .gitignore, since they won't
    be committed to the repository anyway.

    Args:
        file_path: Path to check

    Returns:
        True if file should be skipped, False otherwise
    """
    return is_file_in_gitignore(file_path)


__all__ = ["print_help_with_banner", "is_file_in_gitignore", "should_skip_file_in_hook"]
