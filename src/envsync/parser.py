"""Parser for .env files.

This module provides functionality to parse .env and .env.example files,
handling comments, quotes, multiline values, variable interpolation, and various edge cases.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class EnvEntry:
    """Represents a single entry in a .env file.

    Attributes:
        key: Environment variable name
        value: Variable value (empty string for unset)
        comment: Associated comment (if any)
        line_number: Line number in source file
    """

    key: str
    value: str
    comment: Optional[str]
    line_number: int


def expand_variables(
    value: str,
    env_dict: Dict[str, str],
    allow_os_environ: bool = True,
    max_depth: int = 10,
) -> str:
    """Expand variable references in a value string.

    Supports both ${VAR} and $VAR syntax. Variables are resolved from:
    1. env_dict (parsed .env variables)
    2. os.environ (if allow_os_environ=True)

    Expansion is recursive, so variables can reference other variables.
    To prevent infinite loops, expansion stops after max_depth iterations.

    Args:
        value: String potentially containing variable references
        env_dict: Dictionary of parsed environment variables
        allow_os_environ: Whether to fall back to os.environ
        max_depth: Maximum recursion depth for nested expansions

    Returns:
        String with all variables expanded

    Examples:
        >>> expand_variables("${HOME}/data", {})
        "/Users/username/data"
        >>> expand_variables("redis://${REDIS_HOST}:6379", {"REDIS_HOST": "localhost"})
        "redis://localhost:6379"
        >>> expand_variables("$USER@$DOMAIN", {"USER": "admin", "DOMAIN": "example.com"})
        "admin@example.com"
    """
    if not value:
        return value

    # Pattern matches ${VAR} or $VAR (but not $$)
    pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)"

    def replace_var(match: re.Match[str]) -> str:
        # Group 1 is ${VAR}, group 2 is $VAR
        var_name = match.group(1) or match.group(2)

        # Try env_dict first, then os.environ
        if var_name in env_dict:
            return env_dict[var_name]
        elif allow_os_environ and var_name in os.environ:
            return os.environ[var_name]
        else:
            # Keep original reference if not found
            return match.group(0)

    # Recursively expand until no more variables or max depth reached
    previous = value
    for _ in range(max_depth):
        current = re.sub(pattern, replace_var, previous)
        if current == previous:
            # No more expansions
            break
        previous = current

    return current


class EnvFileParser:
    """Parser for .env files with support for comments and various formats."""

    def __init__(
        self,
        preserve_comments: bool = True,
        expand_vars: bool = True,
        allow_os_environ: bool = True,
    ) -> None:
        """Initialize parser.

        Args:
            preserve_comments: Whether to preserve comments when parsing
            expand_vars: Whether to expand variable references (${VAR} syntax)
            allow_os_environ: Whether to allow expansion from os.environ
        """
        self.preserve_comments = preserve_comments
        self.expand_vars = expand_vars
        self.allow_os_environ = allow_os_environ

    def parse_file(self, file_path: Path) -> Dict[str, EnvEntry]:
        """Parse a .env file.

        Args:
            file_path: Path to .env file

        Returns:
            Dictionary mapping variable names to EnvEntry objects

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content)

    def parse_string(self, content: str) -> Dict[str, EnvEntry]:
        """Parse .env content from a string.

        Args:
            content: .env file content

        Returns:
            Dictionary mapping variable names to EnvEntry objects
        """
        entries: Dict[str, EnvEntry] = {}
        lines = content.splitlines()

        i = 0
        pending_comment: Optional[str] = None

        while i < len(lines):
            line = lines[i]
            line_number = i + 1

            # Skip empty lines
            if not line.strip():
                pending_comment = None
                i += 1
                continue

            # Handle comments
            if line.strip().startswith("#"):
                if self.preserve_comments:
                    comment_text = line.strip()[1:].strip()
                    pending_comment = comment_text
                i += 1
                continue

            # Parse key-value pair
            entry = self._parse_line(line, line_number, pending_comment)
            if entry:
                entries[entry.key] = entry
                pending_comment = None

            i += 1

        # Apply variable expansion if enabled
        if self.expand_vars:
            env_dict = {key: entry.value for key, entry in entries.items()}
            for entry in entries.values():
                entry.value = expand_variables(
                    entry.value,
                    env_dict,
                    self.allow_os_environ,
                )

        return entries

    def _parse_line(self, line: str, line_number: int, comment: Optional[str]) -> Optional[EnvEntry]:
        """Parse a single line from .env file.

        Args:
            line: Line to parse
            line_number: Line number for error reporting
            comment: Associated comment (if any)

        Returns:
            EnvEntry object or None if line is invalid
        """
        # Remove inline comments (but not within quotes)
        line_content = self._remove_inline_comment(line)

        # Check if line contains '='
        if "=" not in line_content:
            return None

        # Split on first '='
        key, _, value = line_content.partition("=")
        key = key.strip()

        # Validate key (must be valid identifier)
        if not self._is_valid_key(key):
            return None

        # Parse value (handle quotes, escapes, etc.)
        value = self._parse_value(value)

        return EnvEntry(key=key, value=value, comment=comment, line_number=line_number)

    def _remove_inline_comment(self, line: str) -> str:
        """Remove inline comments while preserving quotes.

        Args:
            line: Line to process

        Returns:
            Line with inline comment removed
        """
        # Simple implementation: only remove # that are outside quotes
        in_single_quote = False
        in_double_quote = False
        result = []

        for i, char in enumerate(line):
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                result.append(char)
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                result.append(char)
            elif char == "#" and not in_single_quote and not in_double_quote:
                # Found comment start outside quotes
                break
            else:
                result.append(char)

        return "".join(result)

    def _is_valid_key(self, key: str) -> bool:
        """Check if a key is a valid environment variable name.

        Args:
            key: Variable name to validate

        Returns:
            True if valid
        """
        # Must start with letter or underscore, contain only alphanumeric and underscore
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
        return bool(re.match(pattern, key))

    def _parse_value(self, value: str) -> str:
        """Parse a value, handling quotes and escapes.

        Args:
            value: Raw value string

        Returns:
            Parsed value
        """
        value = value.strip()

        # Handle empty value
        if not value:
            return ""

        # Handle quoted values
        if len(value) >= 2:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                # Remove quotes and handle escapes
                quote_char = value[0]
                inner = value[1:-1]

                if quote_char == '"':
                    # Double quotes: process escape sequences
                    inner = self._unescape_value(inner)

                return inner

        # Unquoted value: return as-is (already stripped)
        return value

    def _unescape_value(self, value: str) -> str:
        """Process escape sequences in a value.

        Args:
            value: Value with potential escape sequences

        Returns:
            Value with escapes processed
        """
        # Handle common escape sequences
        value = value.replace("\\n", "\n")
        value = value.replace("\\r", "\r")
        value = value.replace("\\t", "\t")
        value = value.replace('\\"', '"')
        value = value.replace("\\\\", "\\")

        return value


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """Parse a .env file and return key-value pairs.

    Convenience function for simple parsing without metadata.

    Args:
        file_path: Path to .env file

    Returns:
        Dictionary mapping variable names to values
    """
    parser = EnvFileParser()
    entries = parser.parse_file(file_path)
    return {key: entry.value for key, entry in entries.items()}


def compare_env_files(env_file: Path, example_file: Path) -> Tuple[List[str], List[str], List[str]]:
    """Compare .env file against .env.example.

    Args:
        env_file: Path to .env file
        example_file: Path to .env.example file

    Returns:
        Tuple of (missing_vars, extra_vars, common_vars)
        - missing_vars: Variables in example but not in env
        - extra_vars: Variables in env but not in example
        - common_vars: Variables in both files
    """
    env_vars = parse_env_file(env_file) if env_file.exists() else {}
    example_vars = parse_env_file(example_file)

    env_keys = set(env_vars.keys())
    example_keys = set(example_vars.keys())

    missing = sorted(example_keys - env_keys)
    extra = sorted(env_keys - example_keys)
    common = sorted(env_keys & example_keys)

    return missing, extra, common


def format_env_file(entries: Dict[str, EnvEntry], include_comments: bool = True) -> str:
    """Format entries back into .env file format.

    Args:
        entries: Dictionary of entries to format
        include_comments: Whether to include comments

    Returns:
        Formatted .env file content
    """
    lines = []

    # Sort entries by line number for stable output
    sorted_entries = sorted(entries.values(), key=lambda e: e.line_number)

    for entry in sorted_entries:
        # Add comment if present
        if include_comments and entry.comment:
            lines.append(f"# {entry.comment}")

        # Add key-value pair
        # Quote value if it contains spaces or special characters
        value = entry.value
        if needs_quoting(value):
            # Escape special characters
            value = value.replace("\\", "\\\\")
            value = value.replace('"', '\\"')
            value = value.replace("\n", "\\n")
            value = f'"{value}"'

        lines.append(f"{entry.key}={value}")

        # Add blank line after each entry for readability
        if include_comments:
            lines.append("")

    return "\n".join(lines)


def needs_quoting(value: str) -> bool:
    """Check if a value needs to be quoted in .env file.

    Args:
        value: Value to check

    Returns:
        True if value should be quoted
    """
    if not value:
        return False

    # Quote if contains spaces, quotes, or special characters
    special_chars = [" ", '"', "'", "#", "\n", "\r", "\t"]
    return any(char in value for char in special_chars)


def merge_env_files(
    base_file: Path,
    new_vars: Dict[str, str],
    preserve_existing: bool = True,
    preserve_comments: bool = True,
) -> str:
    """Merge new variables into an existing .env file.

    Args:
        base_file: Path to existing .env file
        new_vars: Dictionary of new variables to add
        preserve_existing: Whether to preserve existing values
        preserve_comments: Whether to preserve comments

    Returns:
        Merged .env file content
    """
    # Parse existing file
    if base_file.exists():
        parser = EnvFileParser(preserve_comments=preserve_comments)
        entries = parser.parse_file(base_file)
    else:
        entries = {}

    # Add or update variables
    max_line = max((e.line_number for e in entries.values()), default=0)

    for key, value in new_vars.items():
        if key in entries and preserve_existing:
            # Keep existing value
            continue

        if key in entries:
            # Update existing entry
            entries[key].value = value
        else:
            # Add new entry
            max_line += 1
            entries[key] = EnvEntry(key=key, value=value, comment=None, line_number=max_line)

    # Format and return
    return format_env_file(entries, include_comments=preserve_comments)
