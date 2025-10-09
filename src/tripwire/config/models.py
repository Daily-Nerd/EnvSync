"""Data models for unified configuration management.

This module defines the core data structures used throughout the configuration
abstraction layer, providing a format-agnostic representation of configuration
values and their metadata.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ConfigFormat(Enum):
    """Supported configuration formats.

    v0.4.0 supports .env and TOML formats only, covering 95% of Python projects.
    Additional formats (YAML, JSON, cloud secrets) will be available via plugin
    system in v0.5.0+ if demand is proven.

    See: https://github.com/Daily-Nerd/TripWire/issues for format requests
    """

    ENV = "env"
    TOML = "toml"

    # Future formats (deferred to plugin system v0.5.0+):
    # YAML = "yaml"          # Deferred: Security risk, <5% adoption for env vars
    # JSON = "json"          # Deferred: Poor UX, no adoption for env vars
    # CLOUD_AWS = "aws"      # Deferred: Plugin system (tripwire-aws package)
    # CLOUD_VAULT = "vault"  # Deferred: Plugin system (tripwire-vault package)


@dataclass(frozen=True)
class SourceMetadata:
    """Metadata about where a config value came from.

    This class tracks the origin and context of configuration values,
    enabling features like source attribution, git auditing, and
    secret detection.

    Attributes:
        source_type: Format of the configuration source
        file_path: Path to the source file, if applicable
        line_number: Line number in source file, if known
        last_modified: Last modification timestamp, if available
        is_secret: Whether this appears to be a secret value
        comment: Associated comment from source, if any
    """

    source_type: ConfigFormat
    file_path: Path | None = None
    line_number: int | None = None
    last_modified: float | None = None
    is_secret: bool = False
    comment: str | None = None


@dataclass
class ConfigValue:
    """A configuration value with metadata.

    This class wraps a configuration value along with metadata about its
    origin, enabling format-agnostic configuration management.

    Attributes:
        key: The configuration variable name
        value: The parsed/typed value
        raw_value: Original string representation
        metadata: Source metadata

    Example:
        >>> metadata = SourceMetadata(source_type=ConfigFormat.ENV)
        >>> config = ConfigValue(
        ...     key="PORT",
        ...     value=8000,
        ...     raw_value="8000",
        ...     metadata=metadata
        ... )
        >>> print(config.key)
        PORT
        >>> print(config.value)
        8000
    """

    key: str
    value: Any
    raw_value: str
    metadata: SourceMetadata

    def __str__(self) -> str:
        """String representation returns raw value."""
        return self.raw_value

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ConfigValue(key={self.key!r}, value={self.value!r}, source={self.metadata.source_type.value})"


@dataclass
class ConfigDiff:
    """Difference between two configurations.

    This class represents the result of comparing two configuration sources,
    categorizing variables as added, removed, modified, or unchanged.

    Attributes:
        added: Variables present only in the second configuration
        removed: Variables present only in the first configuration
        modified: Variables with different values (old, new)
        unchanged: Variables with identical values

    Example:
        >>> diff = ConfigDiff(
        ...     added={"NEW_VAR": config_value},
        ...     removed={"OLD_VAR": config_value},
        ...     modified={"PORT": (old_value, new_value)},
        ...     unchanged={}
        ... )
        >>> if diff.has_changes:
        ...     print("Configurations differ!")
    """

    added: dict[str, ConfigValue]
    removed: dict[str, ConfigValue]
    modified: dict[str, tuple[ConfigValue, ConfigValue]]
    unchanged: dict[str, ConfigValue]

    @property
    def has_changes(self) -> bool:
        """Check if there are any differences between configurations."""
        return bool(self.added or self.removed or self.modified)

    def summary(self) -> str:
        """Get a summary of the differences.

        Returns:
            Human-readable summary string

        Example:
            >>> diff.summary()
            '2 added, 1 removed, 3 modified'
        """
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.removed:
            parts.append(f"{len(self.removed)} removed")
        if self.modified:
            parts.append(f"{len(self.modified)} modified")

        if not parts:
            return "No differences"

        return ", ".join(parts)
