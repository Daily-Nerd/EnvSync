"""Protocol definition for configuration source adapters.

This module defines the ConfigSource protocol that all configuration adapters
must implement, ensuring a consistent interface across different formats.
"""

from pathlib import Path
from typing import Protocol

from .models import ConfigFormat, ConfigValue


class ConfigSource(Protocol):
    """Protocol for configuration source adapters.

    All configuration source adapters must implement this protocol to ensure
    consistent behavior across different formats (.env, TOML, etc.).

    The protocol defines methods for loading, saving, and querying capabilities
    of configuration sources.

    Example:
        >>> class CustomSource:
        ...     @property
        ...     def format_name(self) -> ConfigFormat:
        ...         return ConfigFormat.ENV
        ...
        ...     @property
        ...     def file_path(self) -> Optional[Path]:
        ...         return Path(".env")
        ...
        ...     def load(self) -> Dict[str, ConfigValue]:
        ...         return {}
        ...
        ...     def save(self, data: Dict[str, ConfigValue]) -> None:
        ...         pass
        ...
        ...     def supports_feature(self, feature: str) -> bool:
        ...         return feature == "comments"
    """

    @property
    def format_name(self) -> ConfigFormat:
        """Format identifier for this source.

        Returns:
            ConfigFormat enum value indicating the format type
        """
        ...

    @property
    def file_path(self) -> Path | None:
        """Path to configuration file, if applicable.

        Returns:
            Path object for file-based sources, None for non-file sources
            (e.g., environment variables, cloud secrets)
        """
        ...

    def load(self) -> dict[str, ConfigValue]:
        """Load configuration from source.

        Reads configuration data from the source and returns it as a dictionary
        mapping variable names to ConfigValue objects with metadata.

        Returns:
            Dict mapping variable names to ConfigValue objects

        Raises:
            FileNotFoundError: If source file doesn't exist (for file-based sources)
            PermissionError: If source file cannot be read
            ValueError: If source format is invalid
        """
        ...

    def save(self, data: dict[str, ConfigValue]) -> None:
        """Save configuration to source.

        Writes configuration data to the source, preserving existing structure
        where possible (e.g., comments, formatting).

        Args:
            data: Configuration data to save, mapping variable names to ConfigValue objects

        Raises:
            PermissionError: If source cannot be written
            ValueError: If data format is invalid
        """
        ...

    def supports_feature(self, feature: str) -> bool:
        """Check if source supports a specific feature.

        This method allows querying source capabilities to enable feature-specific
        behavior in the repository layer.

        Common features:
            - 'comments': Source preserves inline comments
            - 'multiline': Source supports multiline values
            - 'nested': Source supports nested/hierarchical structure
            - 'typed_values': Source preserves native types (int, bool, etc.)
            - 'sections': Source supports logical grouping/sections

        Args:
            feature: Feature name to query

        Returns:
            True if feature is supported, False otherwise

        Example:
            >>> source.supports_feature('comments')
            True
            >>> source.supports_feature('nested')
            False
        """
        ...
