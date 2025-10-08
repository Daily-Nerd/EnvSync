#!/usr/bin/env python3
"""Release script for TripWire.

This script helps automate the release process by:
1. Validating the current state
2. Updating version numbers
3. Creating git tags
4. Pushing to remote
5. Triggering GitHub Actions workflows

Usage:
    python scripts/release.py 1.0.0
    python scripts/release.py 1.0.0 --prerelease
    python scripts/release.py 1.0.0 --dry-run
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True, interactive: bool = False) -> subprocess.CompletedProcess:
    """Run a command and return the result.

    Args:
        cmd: Command to run as list of strings
        check: If True, exit on non-zero return code
        interactive: If True, don't capture output (allows user interaction like GPG signing)
    """
    print(f"Running: {' '.join(cmd)}")

    if interactive:
        # Don't capture output - allows GPG passphrase prompts to show
        result = subprocess.run(cmd, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        if not interactive:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        sys.exit(1)

    return result


def validate_version(version: str) -> bool:
    """Validate version format (PEP 440 compatible).

    Examples:
        - 1.0.0
        - 1.0.0-rc.1
        - 1.0.0-beta.2
        - 1.0.0-alpha
        - 1.0.0a1, 1.0.0b2, 1.0.0rc3 (PEP 440 style)
    """
    # More permissive pattern that accepts common version formats
    pattern = r"^\d+\.\d+\.\d+(-(rc|alpha|beta|a|b|dev)\.?\d*)?$"
    return bool(re.match(pattern, version))


def check_git_status() -> None:
    """Check that git working directory is clean."""
    result = run_command(["git", "status", "--porcelain"])
    if result.stdout.strip():
        print("Error: Working directory is not clean")
        print("Please commit or stash your changes first")
        sys.exit(1)


def check_branch() -> str:
    """Check current branch and return it."""
    result = run_command(["git", "branch", "--show-current"])
    branch = result.stdout.strip()
    print(f"Current branch: {branch}")
    return branch


def update_version_in_files(version: str) -> None:
    """Update version in pyproject.toml and __init__.py."""
    # Update pyproject.toml
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Replace version in pyproject.toml
    content = re.sub(r'^version = "[^"]*"', f'version = "{version}"', content, flags=re.MULTILINE)

    pyproject_path.write_text(content)
    print(f"Updated version in {pyproject_path} to {version}")

    # Update __init__.py
    init_path = Path("src/tripwire/__init__.py")
    content = init_path.read_text()

    # Replace version in __init__.py
    content = re.sub(r'^__version__ = "[^"]*"', f'__version__ = "{version}"', content, flags=re.MULTILINE)

    init_path.write_text(content)
    print(f"Updated version in {init_path} to {version}")

    # Update cli.py
    cli_path = Path("src/tripwire/cli.py")
    content = cli_path.read_text()

    # Replace version in @click.version_option decorator
    content = re.sub(r'@click\.version_option\(version="[^"]*"', f'@click.version_option(version="{version}"', content)

    cli_path.write_text(content)
    print(f"Updated version in {cli_path} to {version}")


def run_tests() -> None:
    """Run tests to ensure everything works."""
    print("Running tests...")
    run_command(["python", "-m", "pytest", "--cov=tripwire", "--cov-report=term-missing"])
    print("✅ Tests passed")


def run_linting() -> None:
    """Run linting checks using pre-commit (same as CI)."""
    print("Running linting with pre-commit...")
    # Use pre-commit which manages its own tool environments
    run_command(["pre-commit", "run", "--all-files"])
    print("✅ Linting passed")


def commit_changes(version: str, is_prerelease: bool) -> None:
    """Commit version changes."""
    commit_msg = f"Bump version to {version}"
    if is_prerelease:
        commit_msg += " (prerelease)"

    run_command(["git", "add", "pyproject.toml", "src/tripwire/__init__.py", "src/tripwire/cli.py"])
    # Use interactive=True to allow GPG signing prompts to show
    run_command(["git", "commit", "-m", commit_msg], interactive=True)
    print(f"✅ Committed changes: {commit_msg}")


def create_tag(version: str) -> None:
    """Create git tag."""
    tag = f"v{version}"

    # Check if tag already exists
    result = run_command(["git", "tag", "-l", tag], check=False)
    if result.stdout.strip():
        print(f"Error: Tag {tag} already exists")
        sys.exit(1)

    # Use interactive=True to allow GPG signing prompts for annotated tags
    run_command(["git", "tag", "-a", tag, "-m", f"Release {tag}"], interactive=True)
    print(f"✅ Created tag: {tag}")


def push_changes(branch: str, version: str) -> None:
    """Push changes and tags to remote."""
    tag = f"v{version}"

    print(f"Pushing changes to origin/{branch}...")
    run_command(["git", "push", "origin", branch])

    print(f"Pushing tag {tag} to origin...")
    run_command(["git", "push", "origin", tag])

    print("✅ Pushed changes and tag to remote")


def main():
    """Main release function."""
    parser = argparse.ArgumentParser(description="Release TripWire")
    parser.add_argument("version", help="Version to release (e.g., 1.0.0)")
    parser.add_argument("--prerelease", action="store_true", help="Mark as prerelease")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-linting", action="store_true", help="Skip running linting")

    args = parser.parse_args()

    # Validate version
    if not validate_version(args.version):
        print(f"Error: Invalid version format: {args.version}")
        print("Expected format: X.Y.Z or X.Y.Z-prerelease")
        sys.exit(1)

    print(f"🚀 Releasing TripWire {args.version}")
    if args.prerelease:
        print("📦 This will be a prerelease")
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")

    # Check git status
    if not args.dry_run:
        check_git_status()
        branch = check_branch()

        if branch != "main" and not args.prerelease:
            print("Warning: You're not on the main branch")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                sys.exit(1)

    # Update version in files
    if not args.dry_run:
        update_version_in_files(args.version)

    # Run tests and linting
    if not args.dry_run and not args.skip_tests:
        run_tests()

    if not args.dry_run and not args.skip_linting:
        run_linting()

    if args.dry_run:
        print("🔍 DRY RUN - Would have:")
        print(f"  - Updated version to {args.version}")
        print(f"  - Committed changes")
        print(f"  - Created tag v{args.version}")
        print(f"  - Pushed to remote")
        return

    # Commit changes
    commit_changes(args.version, args.prerelease)

    # Create tag
    create_tag(args.version)

    # Push changes
    push_changes(branch, args.version)

    print(f"\n🎉 Successfully released TripWire {args.version}!")
    print(f"📦 PyPI: https://pypi.org/project/tripwire-py/{args.version}/")
    print(f"🏷️  GitHub: https://github.com/Daily-Nerd/TripWire/releases/tag/v{args.version}")
    print("\nThe GitHub Actions workflow will now:")
    print("  1. Build the package")
    print("  2. Upload to PyPI")
    print("  3. Create a GitHub release")
    print("\nYou can monitor progress at:")
    print("  https://github.com/Daily-Nerd/TripWire/actions")


if __name__ == "__main__":
    main()
