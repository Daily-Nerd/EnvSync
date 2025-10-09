"""Adapter for .env file configuration sources.

This module provides an adapter for reading and writing .env files using
python-dotenv, with support for comment preservation and secret detection.
"""

import re
from pathlib import Path

from dotenv import dotenv_values

from ..models import ConfigFormat, ConfigValue, SourceMetadata


class EnvFileSource:
    """Adapter for .env file configuration sources.

    This adapter loads and saves configuration from .env files, preserving
    comments and detecting potential secrets.

    Features:
        - Comment preservation when saving
        - Multiline value support
        - Secret detection based on key names
        - Line number tracking for each variable
        - Graceful handling of missing files

    Example:
        >>> source = EnvFileSource(".env")
        >>> config = source.load()
        >>> print(config["DATABASE_URL"].value)
        postgresql://localhost/mydb
        >>> source.save(config)
    """

    # Patterns that suggest a value might be a secret
    SECRET_PATTERNS = [
        r"SECRET",
        r"PASSWORD",
        r"TOKEN",
        r"API_KEY",
        r"PRIVATE_KEY",
        r"AUTH",
        r"CREDENTIAL",
        r"ENCRYPTION",
        r"SIGNATURE",
        r"OAUTH",
    ]

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the .env file source.

        Args:
            file_path: Path to the .env file
        """
        self.path = Path(file_path)

    @property
    def format_name(self) -> ConfigFormat:
        """Format identifier for this source.

        Returns:
            ConfigFormat.ENV
        """
        return ConfigFormat.ENV

    @property
    def file_path(self) -> Path | None:
        """Path to configuration file.

        Returns:
            Path to the .env file
        """
        return self.path

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from .env file.

        Reads the .env file and creates ConfigValue objects for each variable,
        including metadata such as line numbers and secret detection.

        Returns:
            Dict mapping variable names to ConfigValue objects

        Raises:
            FileNotFoundError: If .env file doesn't exist
            PermissionError: If .env file cannot be read

        Example:
            >>> source = EnvFileSource(".env")
            >>> config = source.load()
            >>> config["PORT"].value
            '8000'
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")

        # Load values using python-dotenv
        values = dotenv_values(str(self.path))

        # Get file modification time
        last_modified = self.path.stat().st_mtime

        # Parse file to get line numbers and comments
        line_data = self._parse_file_structure()

        # Create ConfigValue objects
        config: dict[str, ConfigValue] = {}
        for key, value in values.items():
            if value is None:
                value = ""

            # Get line number and comment
            line_info = line_data.get(key, {})
            line_number_raw = line_info.get("line_number")
            comment_raw = line_info.get("comment")

            # Type narrow: line_number should be int or None
            line_number = line_number_raw if isinstance(line_number_raw, int) else None
            # Type narrow: comment should be str or None
            comment = comment_raw if isinstance(comment_raw, str) else None

            # Detect if this might be a secret
            is_secret = self._is_potential_secret(key)

            metadata = SourceMetadata(
                source_type=ConfigFormat.ENV,
                file_path=self.path,
                line_number=line_number,
                last_modified=last_modified,
                is_secret=is_secret,
                comment=comment,
            )

            config[key] = ConfigValue(key=key, value=value, raw_value=value, metadata=metadata)

        return config

    def save(self, data: dict[str, ConfigValue]) -> None:
        """Save configuration to .env file.

        Writes configuration to the .env file, preserving existing structure,
        comments, and empty lines. Updates existing variables and appends new ones.

        Args:
            data: Configuration data to save

        Raises:
            PermissionError: If .env file cannot be written

        Example:
            >>> source = EnvFileSource(".env")
            >>> config = source.load()
            >>> config["PORT"] = ConfigValue("PORT", "3000", "3000", metadata)
            >>> source.save(config)
        """
        # Read existing file content if it exists
        if self.path.exists():
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
        else:
            lines = []

        # Track which keys have been updated
        updated_keys = set()

        # Update existing lines
        new_lines = []
        for line in lines:
            stripped = line.strip()

            # Preserve comments and empty lines
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            # Parse variable assignment
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
            if match:
                key = match.group(1)
                if key in data:
                    # Update the value
                    value = data[key].raw_value
                    # Preserve any inline comment
                    comment_match = re.search(r"#.*$", line)
                    if comment_match:
                        inline_comment = comment_match.group(0)
                        new_lines.append(f"{key}={value}  {inline_comment}\n")
                    else:
                        new_lines.append(f"{key}={value}\n")
                    updated_keys.add(key)
                else:
                    # Keep the line as-is if key not in data
                    new_lines.append(line)
            else:
                # Keep the line as-is
                new_lines.append(line)

        # Append new keys
        new_keys = set(data.keys()) - updated_keys
        if new_keys:
            # Add blank line before new keys if file isn't empty
            if new_lines and new_lines[-1].strip():
                new_lines.append("\n")

            for key in sorted(new_keys):
                value = data[key].raw_value
                comment: str | None = data[key].metadata.comment
                if comment:
                    new_lines.append(f"{key}={value}  # {comment}\n")
                else:
                    new_lines.append(f"{key}={value}\n")

        # Write back to file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    def supports_feature(self, feature: str) -> bool:
        """Check if source supports a specific feature.

        Supported features:
            - 'comments': Yes, inline comments are preserved
            - 'multiline': Yes, via quoted values or backslash continuation
            - 'nested': No, .env files are flat key-value pairs
            - 'typed_values': No, all values are strings

        Args:
            feature: Feature name to query

        Returns:
            True if feature is supported, False otherwise

        Example:
            >>> source = EnvFileSource(".env")
            >>> source.supports_feature('comments')
            True
            >>> source.supports_feature('nested')
            False
        """
        supported = {"comments", "multiline"}
        return feature in supported

    def _is_potential_secret(self, key: str) -> bool:
        """Check if a variable name suggests it might be a secret.

        Args:
            key: Variable name to check

        Returns:
            True if key matches secret patterns
        """
        key_upper = key.upper()
        return any(re.search(pattern, key_upper) for pattern in self.SECRET_PATTERNS)

    def _parse_file_structure(self) -> dict[str, dict[str, int | str | None]]:
        """Parse .env file to extract line numbers and comments.

        Returns:
            Dict mapping variable names to their line numbers and comments
        """
        if not self.path.exists():
            return {}

        line_data: dict[str, dict[str, int | str | None]] = {}

        with open(self.path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                stripped = line.strip()

                # Skip comments and empty lines
                if not stripped or stripped.startswith("#"):
                    continue

                # Parse variable assignment
                match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
                if match:
                    key = match.group(1)

                    # Extract inline comment if present
                    comment_match = re.search(r"#\s*(.+)$", line)
                    comment = comment_match.group(1).strip() if comment_match else None

                    line_data[key] = {"line_number": line_num, "comment": comment}

        return line_data
