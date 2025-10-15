"""Security audit command for TripWire CLI."""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import click

from tripwire.branding import LOGO_BANNER, get_status_icon
from tripwire.cli.formatters.audit import (
    display_combined_timeline,
    display_single_audit_result,
)
from tripwire.cli.progress import audit_progress
from tripwire.cli.utils.console import console


@click.command(name="audit")
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
def audit(
    secret_name: Optional[str],
    scan_all: bool,
    value: Optional[str],
    max_commits: int,
    strict: bool,
    output_json: bool,
) -> None:
    """Deep forensic analysis of git history for secret leaks.

    Comprehensive investigation tool for security incidents. Analyzes git
    history to show when secrets were added, how long they were exposed,
    and provides detailed remediation steps.

    For quick security checks, use 'tripwire security scan' instead.

    Examples:

        tripwire security audit --all

        tripwire security audit AWS_SECRET_ACCESS_KEY

        tripwire security audit API_KEY --value "sk-abc123..."

        tripwire security audit DATABASE_URL --json
    """
    import json

    from rich.table import Table

    from tripwire.git_audit import analyze_secret_history, generate_remediation_steps
    from tripwire.secrets import scan_env_file

    # Validate arguments
    if not scan_all and not secret_name:
        console.print("[red]Error:[/red] Must provide SECRET_NAME or use --all flag")
        console.print("Try: tripwire audit --help")
        sys.exit(1)

    if scan_all and secret_name:
        console.print("[red]Error:[/red] Cannot use both SECRET_NAME and --all flag")
        console.print("Use either 'tripwire audit SECRET_NAME' or 'tripwire audit --all'")
        sys.exit(1)

    # Auto-detection mode
    if scan_all:
        if not output_json:
            console.print("\n[bold cyan][*] Auto-detecting secrets in .env file...[/bold cyan]\n")

        env_file = Path.cwd() / ".env"
        if not env_file.exists():
            console.print("[red]Error:[/red] .env file not found in current directory")
            console.print("Run 'tripwire init' to create one, or specify a secret name to audit.")
            sys.exit(1)

        # Strategy 1: Schema-aware detection (if .tripwire.toml exists)
        # This finds variables marked with secret=true in the schema
        schema_path = Path.cwd() / ".tripwire.toml"
        schema_detected_secrets = []

        if schema_path.exists():
            try:
                from tripwire.schema import load_schema

                schema = load_schema(schema_path)
                if schema:
                    # Find all variables marked as secret in schema
                    for var_name, var_schema in schema.variables.items():
                        if var_schema.secret:
                            # Create SecretMatch for schema-marked secrets
                            # Use GENERIC_API_SECRET as default type if not detected by pattern
                            from tripwire.secrets import (
                                SecretMatch,
                                SecretType,
                                get_recommendation,
                            )

                            schema_detected_secrets.append(
                                SecretMatch(
                                    secret_type=SecretType.GENERIC_API_SECRET,
                                    variable_name=var_name,
                                    value="[from schema]",  # Placeholder, actual value not needed
                                    line_number=0,
                                    severity="high",  # Schema-marked secrets are high severity by default
                                    recommendation=get_recommendation(SecretType.GENERIC_API_SECRET),
                                )
                            )

                    if not output_json and schema_detected_secrets:
                        console.print(
                            f"[dim]Found {len(schema_detected_secrets)} secret(s) marked in .tripwire.toml schema[/dim]\n"
                        )
            except Exception as e:
                # Schema loading failed, fall back to pattern-based detection only
                if not output_json:
                    console.print(f"[dim]Warning: Could not load schema file: {e}[/dim]\n")

        # Strategy 2: Pattern-based detection (scan .env file for secret patterns)
        detected_secrets = scan_env_file(env_file)

        # Merge strategies: prioritize schema-detected secrets, add pattern-detected ones
        # Create a map of variable names to secrets
        secret_map = {}
        for secret in schema_detected_secrets:
            secret_map[secret.variable_name] = secret

        # Add pattern-detected secrets that aren't already in schema
        for secret in detected_secrets:
            if secret.variable_name not in secret_map:
                secret_map[secret.variable_name] = secret

        # Final list combines both strategies
        detected_secrets = list(secret_map.values())

        if not detected_secrets:
            # JSON output mode - return empty results as JSON
            if output_json:
                json_output = {
                    "total_secrets_found": 0,
                    "secrets": [],
                }
                print(json.dumps(json_output, indent=2))
                return

            # Human-readable output
            status = get_status_icon("valid")
            console.print(f"{status} No secrets detected in .env file")
            console.print("Your environment file appears secure")
            return

        # Display detected secrets summary (only in non-JSON mode)
        if not output_json:
            console.print(f"[yellow][!] Found {len(detected_secrets)} potential secret(s) in .env file[/yellow]\n")

            summary_table = Table(title="Detected Secrets", show_header=True, header_style="bold cyan")
            summary_table.add_column("Variable", style="yellow")
            summary_table.add_column("Type", style="cyan")
            summary_table.add_column("Severity", style="red")

            for secret in detected_secrets:
                summary_table.add_row(
                    secret.variable_name,
                    secret.secret_type.value,
                    secret.severity.upper(),
                )

            console.print(summary_table)
            console.print()

        # Audit each detected secret with progress tracking
        all_results = []

        # Use progress tracking for multi-secret audit (spinner mode - unknown total commits)
        if not output_json and len(detected_secrets) > 0:
            with audit_progress(total_commits=None, console=console) as tracker:
                for idx, secret in enumerate(detected_secrets):
                    console.print(f"\n[bold cyan]{'=' * 70}[/bold cyan]")
                    console.print(
                        f"[bold cyan]Auditing: {secret.variable_name} ({idx+1}/{len(detected_secrets)})[/bold cyan]"
                    )
                    console.print(f"[bold cyan]{'=' * 70}[/bold cyan]\n")

                    try:
                        timeline = analyze_secret_history(
                            secret_name=secret.variable_name,
                            secret_value=None,  # Don't pass value for privacy
                            repo_path=Path.cwd(),
                            max_commits=max_commits,
                        )
                        all_results.append((secret, timeline))

                        # Update progress
                        secrets_found = sum(1 for _, t in all_results if t.total_occurrences > 0)
                        tracker.update(commits_processed=idx + 1, secrets_found=secrets_found)

                    except Exception as e:
                        console.print(f"[red]Error auditing {secret.variable_name}:[/red] {e}")
                        continue

                # Finish with final count
                final_secrets_found = sum(1 for _, t in all_results if t.total_occurrences > 0)
                tracker.finish(total_secrets=final_secrets_found)
        else:
            # JSON mode or no secrets - no progress tracking
            for secret in detected_secrets:
                if not output_json:
                    console.print(f"\n[bold cyan]{'=' * 70}[/bold cyan]")
                    console.print(f"[bold cyan]Auditing: {secret.variable_name}[/bold cyan]")
                    console.print(f"[bold cyan]{'=' * 70}[/bold cyan]\n")

                try:
                    timeline = analyze_secret_history(
                        secret_name=secret.variable_name,
                        secret_value=None,  # Don't pass value for privacy
                        repo_path=Path.cwd(),
                        max_commits=max_commits,
                    )
                    all_results.append((secret, timeline))

                except Exception as e:
                    if not output_json:
                        console.print(f"[red]Error auditing {secret.variable_name}:[/red] {e}")
                    continue

        # JSON output mode (skip visual output)
        if output_json:
            json_output = {
                "total_secrets_found": len(detected_secrets),
                "secrets": [
                    {
                        "variable_name": secret.variable_name,
                        "secret_type": secret.secret_type.value,
                        "severity": secret.severity,
                        "status": "LEAKED" if timeline.total_occurrences > 0 else "CLEAN",
                        "first_seen": timeline.first_seen.isoformat() if timeline.first_seen else None,
                        "last_seen": timeline.last_seen.isoformat() if timeline.last_seen else None,
                        "commits_affected": len(timeline.commits_affected),
                        "files_affected": timeline.files_affected,
                        "branches_affected": timeline.branches_affected,
                        "is_public": timeline.is_in_public_repo,
                        "is_current": timeline.is_currently_in_git,
                    }
                    for secret, timeline in all_results
                ],
            }
            print(json.dumps(json_output, indent=2))
            return

        # Display combined visual timeline first
        if all_results:
            display_combined_timeline(all_results, console)

        # Then display individual results
        for secret, timeline in all_results:
            display_single_audit_result(secret.variable_name, timeline, console)

        # Exit with error in strict mode if secrets found in git history
        if strict:
            has_leaked_secrets = any(timeline.total_occurrences > 0 for _, timeline in all_results)
            if has_leaked_secrets:
                sys.exit(1)

        return

    # Single secret mode
    # At this point secret_name is guaranteed to be non-None due to validation above
    assert secret_name is not None, "secret_name must be provided in single secret mode"

    try:
        from tripwire.git_audit import count_commits, sanitize_git_pattern

        # Build search pattern (same logic as analyze_secret_history)
        if value:
            secret_pattern = re.escape(value)
        else:
            secret_pattern = rf"{re.escape(secret_name)}\s*[:=]\s*['\"]?[^\s'\";]+['\"]?"

        # Sanitize pattern
        sanitized_pattern = sanitize_git_pattern(secret_pattern)

        # Try to estimate commit count for progress bar
        if not output_json:
            console.print(f"\n[bold cyan]Analyzing git history for: {secret_name}[/bold cyan]\n")

        total_commits = count_commits(
            repo_path=Path.cwd(),
            secret_pattern=sanitized_pattern,
            max_commits=max_commits,
        )

        # Use progress tracking (only in non-JSON mode)
        if not output_json:
            with audit_progress(total_commits=total_commits, console=console) as tracker:
                # Start the analysis
                timeline = analyze_secret_history(
                    secret_name=secret_name,
                    secret_value=value,
                    repo_path=Path.cwd(),
                    max_commits=max_commits,
                )

                # Update tracker with final results
                commits_scanned = len(timeline.commits_affected) if timeline.commits_affected else 0
                secrets_found = 1 if timeline.total_occurrences > 0 else 0
                tracker.update(commits_processed=commits_scanned, secrets_found=secrets_found)
                tracker.finish(total_secrets=secrets_found)
        else:
            # JSON mode - no progress display
            timeline = analyze_secret_history(
                secret_name=secret_name,
                secret_value=value,
                repo_path=Path.cwd(),
                max_commits=max_commits,
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # JSON output mode
    if output_json:
        remediation_steps = generate_remediation_steps(timeline, secret_name)

        result = {
            "secret_name": secret_name,
            "status": "LEAKED" if timeline.total_occurrences > 0 else "CLEAN",
            "first_seen": timeline.first_seen.isoformat() if timeline.first_seen else None,
            "last_seen": timeline.last_seen.isoformat() if timeline.last_seen else None,
            "exposure_duration_days": timeline.exposure_duration_days,
            "commits_affected": len(timeline.commits_affected),
            "files_affected": timeline.files_affected,
            "is_public": timeline.is_in_public_repo,
            "is_current": timeline.is_currently_in_git,
            "severity": timeline.severity,
            "branches_affected": timeline.branches_affected,
            "remediation_steps": [
                {
                    "order": step.order,
                    "title": step.title,
                    "description": step.description,
                    "urgency": step.urgency,
                    "command": step.command,
                    "warning": step.warning,
                }
                for step in remediation_steps
            ],
        }

        print(json.dumps(result, indent=2))
        return

    # Display single secret result using helper function
    display_single_audit_result(secret_name, timeline, console)

    # Exit with error in strict mode if secret found in git history
    if strict and timeline.total_occurrences > 0:
        sys.exit(1)


__all__ = ["audit"]
