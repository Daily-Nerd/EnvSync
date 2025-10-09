"""Adapter for TOML file configuration sources.

This module provides an adapter for reading and writing TOML files with
support for nested sections, native type preservation, and secret detection.
"""

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from ..models import ConfigFormat, ConfigValue, SourceMetadata


class TOMLSource:
    """Adapter for TOML file configuration sources.

    This adapter loads and saves configuration from TOML files, supporting
    nested sections, native types, and integration with pyproject.toml.

    Features:
        - Nested section support (e.g., [tool.tripwire])
        - Native type preservation (int, bool, float, list, dict)
        - Dotted key flattening for compatibility with .env format
        - Secret detection based on key names
        - Section isolation (only read/write specified section)

    Example:
        >>> source = TOMLSource("pyproject.toml", section="tool.tripwire")
        >>> config = source.load()
        >>> print(config["database.host"].value)
        localhost
        >>> source.save(config)
    """

    # Patterns that suggest a value might be a secret
    SECRET_PATTERNS = [
        "SECRET",
        "PASSWORD",
        "TOKEN",
        "API_KEY",
        "PRIVATE_KEY",
        "AUTH",
        "CREDENTIAL",
        "ENCRYPTION",
        "SIGNATURE",
        "OAUTH",
    ]

    def __init__(self, file_path: str | Path, section: str = "tool.tripwire") -> None:
        """Initialize the TOML file source.

        Args:
            file_path: Path to the TOML file (e.g., pyproject.toml)
            section: Section path to read from (e.g., "tool.tripwire")
        """
        self.path = Path(file_path)
        self.section = section

    @property
    def format_name(self) -> ConfigFormat:
        """Format identifier for this source.

        Returns:
            ConfigFormat.TOML
        """
        return ConfigFormat.TOML

    @property
    def file_path(self) -> Path | None:
        """Path to configuration file.

        Returns:
            Path to the TOML file
        """
        return self.path

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from TOML file.

        Reads the TOML file, navigates to the specified section, and creates
        ConfigValue objects for each variable. Nested dicts are flattened to
        dotted keys (e.g., {"db": {"host": "localhost"}} becomes "db.host").

        Returns:
            Dict mapping variable names to ConfigValue objects

        Raises:
            FileNotFoundError: If TOML file doesn't exist
            PermissionError: If TOML file cannot be read
            ValueError: If TOML format is invalid or section doesn't exist

        Example:
            >>> source = TOMLSource("pyproject.toml", section="tool.tripwire")
            >>> config = source.load()
            >>> config["database.host"].value
            'localhost'
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.path}")

        # Load TOML file
        with open(self.path, "rb") as f:
            toml_data = tomllib.load(f)

        # Navigate to section
        section_data = self._navigate_to_section(toml_data)

        # Get file modification time
        last_modified = self.path.stat().st_mtime

        # Flatten nested dicts and create ConfigValue objects
        config: dict[str, ConfigValue] = {}
        flattened = self._flatten_dict(section_data)

        for key, value in flattened.items():
            # Detect if this might be a secret
            is_secret = self._is_potential_secret(key)

            # Convert value to string for raw_value
            raw_value = self._value_to_string(value)

            metadata = SourceMetadata(
                source_type=ConfigFormat.TOML,
                file_path=self.path,
                line_number=None,  # TOML parsers don't provide line numbers
                last_modified=last_modified,
                is_secret=is_secret,
                comment=None,  # tomli doesn't preserve comments
            )

            config[key] = ConfigValue(key=key, value=value, raw_value=raw_value, metadata=metadata)

        return config

    def save(self, data: dict[str, ConfigValue]) -> None:
        """Save configuration to TOML file.

        Writes configuration to the TOML file, preserving other sections and
        updating only the specified section. Dotted keys are unflattened to
        nested dicts.

        Args:
            data: Configuration data to save

        Raises:
            PermissionError: If TOML file cannot be written

        Example:
            >>> source = TOMLSource("pyproject.toml", section="tool.tripwire")
            >>> config = source.load()
            >>> config["database.host"] = ConfigValue("database.host", "db.example.com", ...)
            >>> source.save(config)
        """
        # Load existing TOML or create empty dict
        if self.path.exists():
            with open(self.path, "rb") as f:
                toml_data = tomllib.load(f)
        else:
            toml_data = {}

        # Unflatten data to nested dict
        section_data = self._unflatten_dict({key: val.value for key, val in data.items()})

        # Update section in TOML data
        self._update_section(toml_data, section_data)

        # Write back to file
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            tomli_w.dump(toml_data, f)

    def supports_feature(self, feature: str) -> bool:
        """Check if source supports a specific feature.

        Supported features:
            - 'comments': No, tomli doesn't preserve comments
            - 'multiline': Yes, via TOML multiline strings
            - 'nested': Yes, TOML supports nested tables
            - 'typed_values': Yes, TOML preserves native types
            - 'sections': Yes, TOML supports logical sections

        Args:
            feature: Feature name to query

        Returns:
            True if feature is supported, False otherwise

        Example:
            >>> source = TOMLSource("pyproject.toml")
            >>> source.supports_feature('typed_values')
            True
            >>> source.supports_feature('comments')
            False
        """
        supported = {"multiline", "nested", "typed_values", "sections"}
        return feature in supported

    def _navigate_to_section(self, toml_data: dict[str, Any]) -> dict[str, Any]:
        """Navigate to specified section in TOML data.

        Args:
            toml_data: Full TOML data

        Returns:
            Data at the specified section

        Raises:
            ValueError: If section doesn't exist
        """
        parts = self.section.split(".")
        current = toml_data

        for part in parts:
            if part not in current:
                raise ValueError(
                    f"Section '{self.section}' not found in {self.path}. " f"Available sections: {list(current.keys())}"
                )
            current = current[part]

        if not isinstance(current, dict):
            raise ValueError(f"Section '{self.section}' is not a table")

        return current

    def _update_section(self, toml_data: dict[str, Any], section_data: dict[str, Any]) -> None:
        """Update specified section in TOML data.

        Args:
            toml_data: Full TOML data (modified in place)
            section_data: New data for the section
        """
        parts = self.section.split(".")
        current = toml_data

        # Navigate to parent of target section, creating if needed
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Update the target section
        current[parts[-1]] = section_data

    def _flatten_dict(self, data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
        """Flatten nested dict to dotted keys.

        Args:
            data: Nested dict to flatten
            parent_key: Parent key prefix
            sep: Separator for nested keys

        Returns:
            Flattened dict with dotted keys

        Example:
            >>> self._flatten_dict({"db": {"host": "localhost"}})
            {"db.host": "localhost"}
        """
        items: list[tuple[str, Any]] = []

        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))

        return dict(items)

    def _unflatten_dict(self, data: dict[str, Any], sep: str = ".") -> dict[str, Any]:
        """Unflatten dotted keys to nested dict.

        Args:
            data: Flattened dict with dotted keys
            sep: Separator for nested keys

        Returns:
            Nested dict

        Example:
            >>> self._unflatten_dict({"db.host": "localhost"})
            {"db": {"host": "localhost"}}
        """
        result: dict[str, Any] = {}

        for key, value in data.items():
            parts = key.split(sep)
            current = result

            # Navigate/create nested structure
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the final value
            current[parts[-1]] = value

        return result

    def _is_potential_secret(self, key: str) -> bool:
        """Check if a variable name suggests it might be a secret.

        Args:
            key: Variable name to check

        Returns:
            True if key matches secret patterns
        """
        key_upper = key.upper()
        return any(pattern in key_upper for pattern in self.SECRET_PATTERNS)

    def _value_to_string(self, value: Any) -> str:
        """Convert TOML value to string representation.

        Args:
            value: TOML value (int, bool, str, list, dict, etc.)

        Returns:
            String representation of value
        """
        if isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (list, dict)):
            import json

            return json.dumps(value)
        else:
            return str(value)
