"""TripWire CLI - Smart environment variable management.

This module provides the main CLI entry point and command registration.
"""

import click

from tripwire.branding import LOGO_SIMPLE

# Import all commands
from tripwire.cli.commands import (
    analyze,
    check,
    deprecated_audit,
    deprecated_scan,
    diff,
    docs,
    generate,
    init,
    install_hooks,
    plugin,
    schema,
    security,
    sync,
    validate,
)
from tripwire.cli.utils import print_help_with_banner


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
@click.version_option(version="0.13.0", prog_name="tripwire", message=f"{LOGO_SIMPLE}\nVersion: %(version)s")
def main() -> None:
    """TripWire - Catch config errors before they explode.

    Validate environment variables at import time with type safety,
    format validation, secret detection, and git audit capabilities.
    """
    pass


# Register all main commands
main.add_command(init.init)
main.add_command(generate.generate)
main.add_command(check.check)
main.add_command(validate.validate)
main.add_command(sync.sync)
main.add_command(docs.docs)
main.add_command(diff.diff)
main.add_command(install_hooks.install_hooks, name="install-hooks")

# Register command groups
main.add_command(analyze)
main.add_command(schema.schema)
main.add_command(security)
main.add_command(plugin)

# Register deprecated aliases for backwards compatibility
main.add_command(deprecated_scan)
main.add_command(deprecated_audit)

__all__ = ["main"]
