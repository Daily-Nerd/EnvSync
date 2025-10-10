"""Helper functions for TripWire CLI."""

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


__all__ = ["print_help_with_banner"]
