#!/usr/bin/env python3
"""Development setup script for TripWire.

This script sets up the development environment by:
1. Installing pre-commit hooks
2. Setting up git configuration
3. Running initial tests
4. Setting up development tools

Usage:
    python scripts/setup-dev.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        if check:
            sys.exit(1)

    return result


def check_python_version() -> None:
    """Check Python version."""
    if sys.version_info < (3, 11):
        print("Error: Python 3.11 or higher is required")
        sys.exit(1)

    print(f"✅ Python {sys.version.split()[0]} detected")


def install_dependencies() -> None:
    """Install development dependencies."""
    print("Installing development dependencies...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run_command([sys.executable, "-m", "pip", "install", "-e", ".[dev]"])
    print("✅ Dependencies installed")


def install_pre_commit() -> None:
    """Install pre-commit hooks."""
    print("Installing pre-commit hooks...")
    run_command([sys.executable, "-m", "pip", "install", "pre-commit"])
    run_command(["pre-commit", "install"])
    run_command(["pre-commit", "install", "--hook-type", "commit-msg"])
    print("✅ Pre-commit hooks installed")


def setup_git_hooks() -> None:
    """Set up additional git hooks."""
    print("Setting up git hooks...")

    # Create .git/hooks/pre-push
    git_hooks_dir = Path(".git/hooks")
    if git_hooks_dir.exists():
        pre_push_hook = git_hooks_dir / "pre-push"
        pre_push_content = """#!/bin/bash
# Run tests before pushing
echo "Running tests before push..."
python -m pytest --cov=tripwire --cov-report=term-missing
if [ $? -ne 0 ]; then
    echo "Tests failed. Push aborted."
    exit 1
fi
echo "All tests passed. Proceeding with push."
"""
        pre_push_hook.write_text(pre_push_content)
        pre_push_hook.chmod(0o755)
        print("✅ Pre-push hook installed")

    print("✅ Git hooks configured")


def run_initial_tests() -> None:
    """Run initial tests to verify setup."""
    print("Running initial tests...")
    run_command([sys.executable, "-m", "pytest", "--cov=tripwire", "--cov-report=term-missing"])
    print("✅ Initial tests passed")


def run_linting() -> None:
    """Run linting to check code quality."""
    print("Running linting...")
    run_command(["ruff", "check", "."])
    run_command(["black", "--check", "."])
    run_command(["mypy", "src/tripwire"])
    print("✅ Linting passed")


def create_gitignore() -> None:
    """Ensure .gitignore is properly configured."""
    gitignore_path = Path(".gitignore")

    if not gitignore_path.exists():
        gitignore_path.touch()

    content = gitignore_path.read_text()

    # Add common Python ignores if not present
    python_ignores = [
        "# Python",
        "__pycache__/",
        "*.py[cod]",
        "*$py.class",
        "*.so",
        ".Python",
        "build/",
        "develop-eggs/",
        "dist/",
        "downloads/",
        "eggs/",
        ".eggs/",
        "lib/",
        "lib64/",
        "parts/",
        "sdist/",
        "var/",
        "wheels/",
        "*.egg-info/",
        ".installed.cfg",
        "*.egg",
        "",
        "# Virtual environments",
        ".venv/",
        "venv/",
        "ENV/",
        "env/",
        "",
        "# IDE",
        ".vscode/",
        ".idea/",
        "*.swp",
        "*.swo",
        "",
        "# Testing",
        ".coverage",
        ".pytest_cache/",
        "htmlcov/",
        ".tox/",
        ".nox/",
        "",
        "# Environment variables",
        ".env",
        ".env.local",
        ".env.*.local",
        "",
        "# OS",
        ".DS_Store",
        "Thumbs.db",
        "",
        "# Security",
        "bandit-report.json",
        "safety-report.json",
        "pip-audit-report.json",
        "semgrep-report.json",
        "licenses.json",
        "licenses.csv",
        "audit-results.json",
    ]

    needs_update = False
    for ignore in python_ignores:
        if ignore and ignore not in content:
            needs_update = True
            break

    if needs_update:
        content += "\n" + "\n".join(python_ignores)
        gitignore_path.write_text(content)
        print("✅ Updated .gitignore")
    else:
        print("✅ .gitignore is up to date")


def create_vscode_settings() -> None:
    """Create VS Code settings for better development experience."""
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    settings = {
        "python.defaultInterpreterPath": "./venv/bin/python",
        "python.linting.enabled": True,
        "python.linting.pylintEnabled": False,
        "python.linting.flake8Enabled": False,
        "python.linting.mypyEnabled": True,
        "python.formatting.provider": "black",
        "python.formatting.blackArgs": ["--line-length", "100"],
        "python.testing.pytestEnabled": True,
        "python.testing.pytestArgs": ["tests"],
        "python.testing.unittestEnabled": False,
        "editor.formatOnSave": True,
        "editor.codeActionsOnSave": {"source.organizeImports": True},
        "files.exclude": {
            "**/__pycache__": True,
            "**/*.pyc": True,
            ".pytest_cache": True,
            ".coverage": True,
            "htmlcov": True,
            ".mypy_cache": True,
            ".ruff_cache": True,
        },
    }

    settings_path = vscode_dir / "settings.json"
    import json

    settings_path.write_text(json.dumps(settings, indent=2))
    print("✅ VS Code settings created")


def main():
    """Main setup function."""
    print("🚀 Setting up TripWire development environment...")

    # Check Python version
    check_python_version()

    # Install dependencies
    install_dependencies()

    # Install pre-commit hooks
    install_pre_commit()

    # Set up git hooks
    setup_git_hooks()

    # Create/update .gitignore
    create_gitignore()

    # Create VS Code settings
    create_vscode_settings()

    # Run initial tests
    run_initial_tests()

    # Run linting
    run_linting()

    print("\n🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("  1. Make your changes")
    print("  2. Run tests: pytest")
    print("  3. Run linting: ruff check . && black . && mypy src/tripwire")
    print("  4. Commit changes (pre-commit hooks will run automatically)")
    print("  5. Push to trigger CI/CD")
    print("\nUseful commands:")
    print("  - Run tests: pytest")
    print("  - Run linting: ruff check .")
    print("  - Format code: black .")
    print("  - Type check: mypy src/tripwire")
    print("  - Run all checks: pre-commit run --all-files")
    print("  - Release: python scripts/release.py 1.0.0")


if __name__ == "__main__":
    main()
