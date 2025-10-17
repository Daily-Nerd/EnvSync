"""Shared constants for TripWire."""

# Directories to skip during file scanning
SKIP_DIRS = {
    ".venv",
    "venv",
    ".virtualenv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".git",
    ".hg",
    ".svn",
    "build",
    "dist",
    ".eggs",
    "node_modules",
    ".idea",
    ".vscode",
}
