"""Plugin base classes and protocols.

This module defines the core interfaces that all TripWire plugins must implement,
as well as metadata structures for plugin registration and discovery.

Design Pattern:
    - Protocol: EnvSourcePlugin defines the interface all plugins must follow
    - Data Class: PluginMetadata encapsulates plugin information
    - Abstract Base Class: PluginInterface provides a concrete base for plugins
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

from tripwire.plugins.errors import PluginAPIError, PluginValidationError


@dataclass(frozen=True)
class PluginMetadata:
    """Metadata describing a TripWire plugin.

    This dataclass contains all information needed to identify, document,
    and validate a plugin. Frozen=True ensures immutability after creation.

    Attributes:
        name: Unique plugin identifier (e.g., "vault", "aws-secrets")
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author name or organization
        description: Human-readable plugin description
        homepage: Optional URL to plugin documentation/homepage
        license: Optional license identifier (e.g., "MIT", "Apache-2.0")
        min_tripwire_version: Minimum TripWire version required (default: "0.10.0")
        tags: Optional list of tags for categorization (e.g., ["cloud", "secrets"])

    Example:
        >>> metadata = PluginMetadata(
        ...     name="vault",
        ...     version="1.0.0",
        ...     author="Acme Corp",
        ...     description="HashiCorp Vault integration",
        ...     homepage="https://github.com/acme/tripwire-vault",
        ...     license="MIT",
        ...     min_tripwire_version="0.10.0",
        ...     tags=["secrets", "vault", "cloud"]
        ... )
    """

    name: str
    version: str
    author: str
    description: str
    homepage: str | None = None
    license: str | None = None
    min_tripwire_version: str = "0.10.0"
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate metadata after initialization.

        Raises:
            PluginValidationError: If metadata is invalid
        """
        errors: list[str] = []

        # Validate required string fields are non-empty
        if not self.name or not self.name.strip():
            errors.append("Plugin name cannot be empty")
        if not self.version or not self.version.strip():
            errors.append("Plugin version cannot be empty")
        if not self.author or not self.author.strip():
            errors.append("Plugin author cannot be empty")
        if not self.description or not self.description.strip():
            errors.append("Plugin description cannot be empty")

        # Validate name format (lowercase, alphanumeric, hyphens only)
        if self.name and not all(c.isalnum() or c in "-_" for c in self.name):
            errors.append(
                f"Plugin name '{self.name}' must contain only alphanumeric characters, " "hyphens, and underscores"
            )

        # Validate version format (basic semantic versioning check)
        if self.version:
            parts = self.version.split(".")
            if len(parts) < 2 or not all(part.isdigit() for part in parts[:2]):
                errors.append(
                    f"Plugin version '{self.version}' must follow semantic versioning " "(e.g., '1.0.0' or '1.0')"
                )

        if errors:
            raise PluginValidationError(self.name or "unknown", errors)


class EnvSourcePlugin(Protocol):
    """Protocol defining the interface all TripWire plugins must implement.

    This protocol uses Python's structural subtyping (PEP 544) to define
    the contract for plugins without requiring explicit inheritance.

    Plugins must implement:
    1. metadata property returning PluginMetadata
    2. load() method returning environment variables
    3. validate_config() method for configuration validation

    Example Implementation:
        >>> class VaultEnvSource:
        ...     def __init__(self, url: str, token: str):
        ...         self.url = url
        ...         self.token = token
        ...         self._metadata = PluginMetadata(
        ...             name="vault",
        ...             version="1.0.0",
        ...             author="Acme Corp",
        ...             description="HashiCorp Vault integration"
        ...         )
        ...
        ...     @property
        ...     def metadata(self) -> PluginMetadata:
        ...         return self._metadata
        ...
        ...     def load(self) -> dict[str, str]:
        ...         # Load secrets from Vault
        ...         return {"DATABASE_URL": "postgresql://..."}
        ...
        ...     def validate_config(self, config: dict[str, Any]) -> bool:
        ...         required = ["url", "token"]
        ...         return all(key in config for key in required)
    """

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        This property provides information about the plugin for registration,
        discovery, and validation purposes.

        Returns:
            PluginMetadata with plugin information

        Example:
            >>> plugin = VaultEnvSource(url="...", token="...")
            >>> print(plugin.metadata.name)
            'vault'
        """
        ...

    def load(self) -> dict[str, str]:
        """Load environment variables from the plugin source.

        This method is called by TripWire to retrieve environment variables
        from the plugin's source (vault, cloud secrets manager, etc.).

        Returns:
            Dictionary mapping environment variable names to values

        Raises:
            PluginAPIError: If loading fails due to plugin error
            Any other exception: Plugin-specific errors

        Example:
            >>> plugin = VaultEnvSource(url="...", token="...")
            >>> env_vars = plugin.load()
            >>> print(env_vars["DATABASE_URL"])
            'postgresql://localhost/mydb'

        Note:
            This method should NOT modify os.environ directly. TripWire's
            EnvFileLoader will handle environment variable injection.
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        This method checks whether the provided configuration contains
        all required parameters and whether they are valid.

        Args:
            config: Configuration dictionary for the plugin

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid

        Example:
            >>> plugin = VaultEnvSource(url="...", token="...")
            >>> config = {"url": "https://vault.example.com", "token": "hvs.xxx"}
            >>> is_valid = plugin.validate_config(config)
            True
        """
        ...


class PluginInterface(ABC):
    """Abstract base class providing a concrete foundation for plugins.

    This class implements the EnvSourcePlugin protocol and provides:
    - Default metadata storage
    - Helper methods for common operations
    - Template methods for subclass customization

    Subclasses must implement:
    - load() method to retrieve environment variables
    - validate_config() method to validate configuration

    Example:
        >>> class MyPlugin(PluginInterface):
        ...     def __init__(self, api_key: str):
        ...         metadata = PluginMetadata(
        ...             name="myplugin",
        ...             version="1.0.0",
        ...             author="Me",
        ...             description="My custom plugin"
        ...         )
        ...         super().__init__(metadata)
        ...         self.api_key = api_key
        ...
        ...     def load(self) -> dict[str, str]:
        ...         # Implementation
        ...         return {"KEY": "value"}
        ...
        ...     def validate_config(self, config: dict[str, Any]) -> bool:
        ...         return "api_key" in config
    """

    def __init__(self, metadata: PluginMetadata) -> None:
        """Initialize plugin with metadata.

        Args:
            metadata: Plugin metadata
        """
        self._metadata = metadata

    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata.

        Returns:
            PluginMetadata instance
        """
        return self._metadata

    @abstractmethod
    def load(self) -> dict[str, str]:
        """Load environment variables from the plugin source.

        This method must be implemented by subclasses to provide
        the core functionality of loading environment variables.

        Returns:
            Dictionary of environment variables

        Raises:
            PluginAPIError: If loading fails
        """
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate plugin configuration.

        This method must be implemented by subclasses to validate
        their specific configuration requirements.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid

        Raises:
            PluginValidationError: If invalid
        """
        pass

    def __repr__(self) -> str:
        """Return string representation of plugin.

        Returns:
            String representation
        """
        return f"<{self.__class__.__name__} " f"name='{self._metadata.name}' " f"version='{self._metadata.version}'>"
