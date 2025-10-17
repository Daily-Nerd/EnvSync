"""CLI commands for TripWire."""

import click

from tripwire.cli.commands import analyze as analyze_module
from tripwire.cli.commands import plugin as plugin_module
from tripwire.cli.commands import security as security_module

# Import the actual security commands for deprecated aliases
from tripwire.cli.commands.security import audit as security_audit
from tripwire.cli.commands.security import scan as security_scan


def create_deprecated_scan() -> click.Command:
    """Create deprecated scan command that redirects to security scan.

    This provides backwards compatibility for the old 'tripwire scan' command.
    Shows a deprecation warning and forwards to 'tripwire security scan'.
    """

    @click.command(name="scan", hidden=True)
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
    @click.pass_context
    def scan(ctx: click.Context, strict: bool, depth: int) -> None:
        """[DEPRECATED] Use 'tripwire security scan' instead."""
        # Print warning to stderr so it doesn't interfere with JSON output
        click.echo("⚠️  Warning: 'tripwire scan' is deprecated.", err=True)
        click.echo("   Use 'tripwire security scan' instead.", err=True)
        click.echo("   This command will be removed in v1.0.0", err=True)
        click.echo("", err=True)
        # Forward to the actual security scan command
        ctx.invoke(security_scan.scan, strict=strict, depth=depth)

    return scan


def create_deprecated_audit() -> click.Command:
    """Create deprecated audit command that redirects to security audit.

    This provides backwards compatibility for the old 'tripwire audit' command.
    Shows a deprecation warning and forwards to 'tripwire security audit'.
    """

    @click.command(name="audit", hidden=True)
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
        "--strict",
        is_flag=True,
        help="Exit with error if secrets found in git history",
    )
    @click.option(
        "--json",
        "output_json",
        is_flag=True,
        help="Output as JSON",
    )
    @click.pass_context
    def audit(
        ctx: click.Context,
        secret_name: str | None,
        scan_all: bool,
        value: str | None,
        max_commits: int,
        strict: bool,
        output_json: bool,
    ) -> None:
        """[DEPRECATED] Use 'tripwire security audit' instead."""
        # Only print warning if not using JSON output (to avoid breaking JSON parsing)
        if not output_json:
            # Print warning to stderr so it doesn't interfere with JSON output
            click.echo("⚠️  Warning: 'tripwire audit' is deprecated.", err=True)
            click.echo("   Use 'tripwire security audit' instead.", err=True)
            click.echo("   This command will be removed in v1.0.0", err=True)
            click.echo("", err=True)
        # Forward to the actual security audit command
        ctx.invoke(
            security_audit.audit,
            secret_name=secret_name,
            scan_all=scan_all,
            value=value,
            max_commits=max_commits,
            strict=strict,
            output_json=output_json,
        )

    return audit


# Create deprecated command instances
deprecated_scan = create_deprecated_scan()
deprecated_audit = create_deprecated_audit()

# Export command groups
analyze = analyze_module.analyze
security = security_module.security
plugin = plugin_module.plugin

__all__ = ["analyze", "security", "plugin", "deprecated_scan", "deprecated_audit"]
