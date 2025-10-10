#!/usr/bin/env python3
"""Release script for TripWire.

This script helps automate the release process by:
1. Validating the current state (including CHANGELOG.md)
2. Updating version numbers
3. Creating git tags (with changelog content)
4. Pushing to remote
5. Triggering GitHub Actions workflows

Usage:
    python scripts/release.py 1.0.0
    python scripts/release.py 1.0.0 --prerelease
    python scripts/release.py 1.0.0 --dry-run
    python scripts/release.py 1.0.0 --skip-changelog-check
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

    # Update cli/__init__.py (new modular structure as of v0.7.0)
    cli_path = Path("src/tripwire/cli/__init__.py")
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

    run_command(["git", "add", "pyproject.toml", "src/tripwire/__init__.py", "src/tripwire/cli/__init__.py"])
    # Use interactive=True to allow GPG signing prompts to show
    run_command(["git", "commit", "-m", commit_msg], interactive=True)
    print(f"✅ Committed changes: {commit_msg}")


def validate_changelog(version: str) -> bool:
    """Validate that CHANGELOG.md has an entry for this version.

    Returns:
        True if changelog is valid, False otherwise
    """
    changelog_path = Path("CHANGELOG.md")

    if not changelog_path.exists():
        print("⚠️  Warning: CHANGELOG.md not found")
        return False

    # Use the validation script if it exists
    validation_script = Path(".github/scripts/validate_changelog.sh")
    if validation_script.exists():
        result = run_command(["bash", str(validation_script), version], check=False)
        return result.returncode == 0

    # Fallback: Simple check for version header
    content = changelog_path.read_text()
    version_pattern = rf"## \[{re.escape(version)}\]"

    if not re.search(version_pattern, content):
        print(f"⚠️  Warning: No entry found for version {version} in CHANGELOG.md")
        print(f"   Expected to find: ## [{version}]")
        return False

    return True


def get_changelog_content(version: str) -> str:
    """Extract changelog content for this version.

    Returns:
        Changelog content as string, or generic message if extraction fails
    """
    # Use the extraction script if it exists
    extraction_script = Path(".github/scripts/extract_changelog.sh")
    if extraction_script.exists():
        result = run_command(["bash", str(extraction_script), version], check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    # Fallback: Try to extract manually
    changelog_path = Path("CHANGELOG.md")
    if changelog_path.exists():
        content = changelog_path.read_text()

        # Find the section for this version
        version_pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|$)"
        match = re.search(version_pattern, content, re.DOTALL)

        if match:
            return match.group(1).strip()

    # Generic fallback
    return f"Release {version}"


def create_tag(version: str, skip_changelog: bool = False) -> None:
    """Create git tag with changelog content as message."""
    tag = f"v{version}"

    # Check if tag already exists
    result = run_command(["git", "tag", "-l", tag], check=False)
    if result.stdout.strip():
        print(f"Error: Tag {tag} already exists")
        sys.exit(1)

    # Get tag message from changelog
    if skip_changelog:
        tag_message = f"Release {tag}"
    else:
        tag_message = get_changelog_content(version)
        if not tag_message or tag_message == f"Release {version}":
            print("⚠️  Using generic tag message (no changelog content found)")

    # Create annotated tag with changelog content
    # Use interactive=True to allow GPG signing prompts for annotated tags
    run_command(["git", "tag", "-a", tag, "-m", tag_message], interactive=True)
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
    parser.add_argument("--skip-changelog-check", action="store_true", help="Skip CHANGELOG.md validation")

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

    # Validate CHANGELOG.md
    if not args.dry_run and not args.skip_changelog_check:
        print("📝 Validating CHANGELOG.md...")
        if not validate_changelog(args.version):
            print("\n❌ CHANGELOG.md validation failed!")
            print("\nPlease ensure CHANGELOG.md has an entry for this version:")
            print(f"   ## [{args.version}] - YYYY-MM-DD")
            print("\nSee docs/CHANGELOG_WORKFLOW.md for guidance.")
            print("\nTo skip this check, use --skip-changelog-check")
            sys.exit(1)
        print("✅ CHANGELOG.md validated")

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
        if not args.skip_changelog_check:
            print(f"  - Validated CHANGELOG.md for version {args.version}")
        print(f"  - Updated version to {args.version}")
        print(f"  - Committed changes")
        print(f"  - Created tag v{args.version} with changelog content")
        print(f"  - Pushed to remote")
        return

    # Commit changes
    commit_changes(args.version, args.prerelease)

    # Create tag (with changelog content if available)
    create_tag(args.version, skip_changelog=args.skip_changelog_check)

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
