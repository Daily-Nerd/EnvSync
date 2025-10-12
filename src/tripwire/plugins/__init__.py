"""TripWire plugin system for extensible environment variable sources.

This package provides a plugin architecture that allows community developers to
extend TripWire with custom environment variable sources (cloud secrets managers,
vaults, remote configuration servers, etc.).

Key Features:
    - Entry point-based plugin discovery
    - Thread-safe plugin registration
    - API compatibility validation
    - Security sandboxing to prevent malicious plugins
    - Comprehensive error handling

Architecture:
    - base: Protocol and metadata definitions
    - errors: Exception hierarchy for plugin errors
    - plugin_system: Registry, loader, validator, and sandbox (in core/plugin_system.py)

Example Usage:
    Basic plugin usage:
        >>> from tripwire import TripWire
        >>> from tripwire.plugins import PluginRegistry
        >>>
        >>> # Auto-discover plugins from entry points
        >>> TripWire.discover_plugins()
        >>>
        >>> # Get a plugin class
        >>> VaultPlugin = PluginRegistry.get_plugin("vault")
        >>>
        >>> # Create plugin instance
        >>> vault = VaultPlugin(url="https://vault.example.com", token="...")
        >>>
        >>> # Use with TripWire
        >>> env = TripWire(sources=[vault])
        >>> DATABASE_URL = env.require("DATABASE_URL")

    Creating a custom plugin:
        >>> from tripwire.plugins import PluginMetadata, PluginInterface
        >>>
        >>> class MyCustomSource(PluginInterface):
        ...     def __init__(self, api_key: str):
        ...         metadata = PluginMetadata(
        ...             name="mycustom",
        ...             version="1.0.0",
        ...             author="Me",
        ...             description="My custom source"
        ...         )
        ...         super().__init__(metadata)
        ...         self.api_key = api_key
        ...
        ...     def load(self) -> dict[str, str]:
        ...         # Fetch from custom source
        ...         return {"MY_VAR": "value"}
        ...
        ...     def validate_config(self, config: dict[str, Any]) -> bool:
        ...         return "api_key" in config

    Registering a plugin in pyproject.toml:
        [project.entry-points."tripwire.plugins"]
        vault = "tripwire_vault:VaultEnvSource"
        aws = "tripwire_aws:AWSSecretsSource"

Version History:
    0.10.0: Initial plugin system implementation
        - Plugin discovery via entry points
        - PluginRegistry for plugin management
        - Security sandboxing
        - API compatibility validation
"""

from tripwire.plugins.base import EnvSourcePlugin, PluginInterface, PluginMetadata
from tripwire.plugins.errors import (
    PluginAPIError,
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    PluginSecurityError,
    PluginValidationError,
    PluginVersionError,
)
from tripwire.plugins.registry import (
    PluginInstaller,
    PluginRegistryClient,
    PluginRegistryEntry,
    PluginRegistryIndex,
    PluginVersionInfo,
)

__all__ = [
    # Base classes and protocols
    "PluginMetadata",
    "EnvSourcePlugin",
    "PluginInterface",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "PluginSecurityError",
    "PluginAPIError",
    "PluginLoadError",
    "PluginVersionError",
    # Registry
    "PluginVersionInfo",
    "PluginRegistryEntry",
    "PluginRegistryIndex",
    "PluginRegistryClient",
    "PluginInstaller",
]

__version__ = "0.10.0"
