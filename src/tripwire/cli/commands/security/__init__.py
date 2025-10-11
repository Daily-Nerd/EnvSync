"""Security command group for TripWire CLI.

This module provides security-focused commands for secret detection,
git history auditing, and future security features.
"""

import click

from tripwire.cli.commands.security import audit, scan


@click.group(name="security")
def security() -> None:
    """Security management: scan for secrets, audit git history, and more.

    The security command group provides tools for protecting your codebase
    from accidental secret exposure:

    \b
    Commands:
      scan   - Quick security check (pre-commit, CI/CD)
      audit  - Deep forensic analysis (incident response)

    \b
    Use Cases:
      - Pre-commit hook: tripwire security scan --strict
      - CI/CD pipeline: tripwire security scan --depth 50
      - Security incident: tripwire security audit --all
      - Investigate secret: tripwire security audit AWS_SECRET_KEY

    \b
    Future Commands (planned):
      - rotate   - Automated secret rotation
      - report   - Security compliance reports
      - baseline - Establish security baseline
    """
    pass


# Add subcommands to the group
security.add_command(scan.scan)
security.add_command(audit.audit)

__all__ = ["security"]
