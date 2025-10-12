"""Mock plugins for testing the plugin system.

This module provides various test plugins to validate plugin loading,
validation, and execution.
"""

from typing import Any

from tripwire.plugins import PluginInterface, PluginMetadata
from tripwire.plugins.errors import PluginAPIError, PluginValidationError


class MockValidPlugin(PluginInterface):
    """A valid mock plugin for testing.

    This plugin implements all required methods correctly and can be used
    to test successful plugin loading and execution.
    """

    def __init__(self, api_key: str = "test-key", url: str = "https://example.com") -> None:
        """Initialize the mock plugin.

        Args:
            api_key: API key for authentication
            url: Service URL
        """
        metadata = PluginMetadata(
            name="mock-valid",
            version="1.0.0",
            author="TripWire Test Suite",
            description="A valid mock plugin for testing",
            homepage="https://github.com/test/mock-plugin",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["test", "mock"],
        )
        super().__init__(metadata)
        self.api_key = api_key
        self.url = url

    def load(self) -> dict[str, str]:
        """Load mock environment variables.

        Returns:
            Dictionary of mock environment variables
        """
        return {
            "MOCK_API_KEY": self.api_key,
            "MOCK_URL": self.url,
            "MOCK_LOADED": "true",
        }

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid

        Raises:
            PluginValidationError: If configuration is invalid
        """
        required = ["api_key", "url"]
        missing = [key for key in required if key not in config]

        if missing:
            raise PluginValidationError(self.metadata.name, [f"Missing required config key: {key}" for key in missing])

        return True


class MockInvalidPlugin:
    """An invalid mock plugin that doesn't implement the protocol.

    This plugin is missing required methods and should fail validation.
    """

    def __init__(self) -> None:
        """Initialize the invalid plugin."""
        self.name = "mock-invalid"

    # Missing: metadata property
    # Missing: load() method
    # Missing: validate_config() method


class MockNoMetadataPlugin:
    """A plugin with no metadata property."""

    def __init__(self) -> None:
        """Initialize the plugin."""
        pass

    def load(self) -> dict[str, str]:
        """Load environment variables."""
        return {}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True


class MockFailingLoadPlugin(PluginInterface):
    """A plugin that raises an error during load().

    This plugin is used to test error handling when plugin loading fails.
    """

    def __init__(self) -> None:
        """Initialize the failing plugin."""
        metadata = PluginMetadata(
            name="mock-failing-load",
            version="1.0.0",
            author="TripWire Test Suite",
            description="A plugin that fails during load",
        )
        super().__init__(metadata)

    def load(self) -> dict[str, str]:
        """Load environment variables (raises error).

        Raises:
            PluginAPIError: Always raised to simulate load failure
        """
        raise PluginAPIError(self.metadata.name, "load", None, "Simulated load failure for testing")

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True


class MockDangerousPlugin(PluginInterface):
    """A plugin with dangerous operations (security test).

    This plugin contains patterns that should be flagged by the security
    sandbox (subprocess, eval, etc.).
    """

    def __init__(self) -> None:
        """Initialize the dangerous plugin."""
        metadata = PluginMetadata(
            name="mock-dangerous",
            version="1.0.0",
            author="TripWire Test Suite",
            description="A plugin with dangerous operations",
        )
        super().__init__(metadata)

    def load(self) -> dict[str, str]:
        """Load environment variables (contains dangerous code).

        Returns:
            Dictionary of environment variables
        """
        # This should be flagged by security checks
        import subprocess  # noqa: F401

        # Simulate dangerous operations
        return {"DANGEROUS": "true"}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True


class MockVersionIncompatiblePlugin(PluginInterface):
    """A plugin that requires a newer TripWire version.

    This plugin is used to test version compatibility checking.
    """

    def __init__(self) -> None:
        """Initialize the version-incompatible plugin."""
        metadata = PluginMetadata(
            name="mock-version-incompatible",
            version="1.0.0",
            author="TripWire Test Suite",
            description="A plugin requiring a newer TripWire version",
            min_tripwire_version="99.0.0",  # Unrealistic future version
        )
        super().__init__(metadata)

    def load(self) -> dict[str, str]:
        """Load environment variables."""
        return {"VERSION_TEST": "true"}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True


class MockSimplePlugin(PluginInterface):
    """A simple plugin with no init parameters.

    This plugin can be instantiated without arguments, useful for
    testing metadata caching and plugin listing.
    """

    def __init__(self) -> None:
        """Initialize the simple plugin."""
        metadata = PluginMetadata(
            name="mock-simple",
            version="1.0.0",
            author="TripWire Test Suite",
            description="A simple mock plugin",
        )
        super().__init__(metadata)

    def load(self) -> dict[str, str]:
        """Load environment variables."""
        return {"SIMPLE_TEST": "true"}

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        return True
