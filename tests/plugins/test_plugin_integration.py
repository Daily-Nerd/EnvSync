"""Integration tests for plugin system with TripWireV2.

Tests cover:
- Using plugins as EnvSource with TripWireV2
- Plugin discovery integration
- EnvFileLoader with plugin sources
- End-to-end plugin workflow
"""

import os
from pathlib import Path

import pytest

from tests.plugins.fixtures.mock_plugin import MockSimplePlugin, MockValidPlugin
from tripwire import TripWire
from tripwire.core import PluginRegistry
from tripwire.core.loader import EnvFileLoader
from tripwire.exceptions import MissingVariableError


class TestPluginWithTripWireV2:
    """Tests for using plugins with TripWireV2."""

    def setup_method(self):
        """Set up test environment."""
        PluginRegistry.clear()
        # Clear environment variables set by previous tests
        for key in list(os.environ.keys()):
            if key.startswith("MOCK_") or key.startswith("TEST_") or key == "NONEXISTENT_VAR":
                del os.environ[key]

    def teardown_method(self):
        """Clean up after tests."""
        PluginRegistry.clear()
        # Clear environment variables
        for key in list(os.environ.keys()):
            if key.startswith("MOCK_") or key.startswith("TEST_"):
                del os.environ[key]

    def test_tripwire_with_single_plugin_source(self):
        """Test TripWireV2 with a single plugin as source."""
        # Create plugin instance
        plugin = MockValidPlugin(api_key="test-api-key", url="https://test.example.com")

        # Create TripWireV2 with plugin source
        env = TripWire(sources=[plugin], auto_load=True)

        # Variables should be loaded from plugin
        mock_api_key = env.require("MOCK_API_KEY")
        mock_url = env.require("MOCK_URL")
        mock_loaded = env.require("MOCK_LOADED")

        assert mock_api_key == "test-api-key"
        assert mock_url == "https://test.example.com"
        assert mock_loaded == "true"

    def test_tripwire_with_multiple_plugin_sources(self):
        """Test TripWireV2 with multiple plugin sources."""
        # Create two plugin instances
        plugin1 = MockValidPlugin(api_key="key1", url="https://example1.com")
        plugin2 = MockSimplePlugin()

        # Create TripWireV2 with both plugins
        env = TripWire(sources=[plugin1, plugin2], auto_load=True)

        # Variables from both plugins should be available
        assert env.require("MOCK_API_KEY") == "key1"
        assert env.require("MOCK_URL") == "https://example1.com"
        assert env.require("SIMPLE_TEST") == "true"

    def test_tripwire_with_plugin_missing_variable(self):
        """Test that missing variable raises error even with plugin."""
        from tripwire.exceptions import TripWireMultiValidationError, ValidationError

        plugin = MockSimplePlugin()
        env = TripWire(sources=[plugin], auto_load=True)

        # Variable not provided by plugin should raise error
        # With error collection, we need to finalize to trigger the error
        with pytest.raises((MissingVariableError, TripWireMultiValidationError, ValidationError)):
            env.require("NONEXISTENT_VAR")
            env.finalize()

    def test_tripwire_with_plugin_type_coercion(self):
        """Test type coercion with plugin-loaded variables."""
        plugin = MockValidPlugin()
        env = TripWire(sources=[plugin], auto_load=True)

        # String value should be coerced to bool
        mock_loaded: bool = env.require("MOCK_LOADED", type=bool)
        assert mock_loaded is True

    def test_tripwire_with_plugin_validation(self):
        """Test validation with plugin-loaded variables."""
        plugin = MockValidPlugin(url="https://secure.example.com")
        env = TripWire(sources=[plugin], auto_load=True)

        # Validate URL format
        mock_url = env.require("MOCK_URL", format="url")
        assert mock_url == "https://secure.example.com"

    def test_envfileloader_with_plugin_sources(self):
        """Test EnvFileLoader with plugin sources."""
        plugin = MockValidPlugin()
        loader = EnvFileLoader([plugin], strict=False)

        # Load all sources
        loader.load_all()

        # Variables should be in environment
        assert os.getenv("MOCK_API_KEY") == "test-key"
        assert os.getenv("MOCK_URL") == "https://example.com"


class TestPluginDiscovery:
    """Tests for plugin discovery integration with TripWire."""

    def setup_method(self):
        """Set up test environment."""
        PluginRegistry.clear()

    def teardown_method(self):
        """Clean up after tests."""
        PluginRegistry.clear()

    def test_discover_plugins_method_exists(self):
        """Test that TripWire.discover_plugins() method exists."""
        assert hasattr(TripWire, "discover_plugins")
        assert callable(TripWire.discover_plugins)

    def test_discover_plugins_executes_without_error(self):
        """Test that discover_plugins() executes without error."""
        # Should not raise any exceptions
        TripWire.discover_plugins()

    def test_manual_plugin_registration_and_usage(self):
        """Test manually registering and using a plugin."""
        # Register plugin manually
        PluginRegistry.register_plugin("test-manual", MockValidPlugin)

        # Retrieve plugin class
        PluginClass = PluginRegistry.get_plugin("test-manual")

        # Create instance and use with TripWire
        plugin_instance = PluginClass(api_key="manual-key")
        env = TripWire(sources=[plugin_instance], auto_load=True)

        assert env.require("MOCK_API_KEY") == "manual-key"


class TestPluginWorkflow:
    """End-to-end workflow tests for plugin system."""

    def setup_method(self):
        """Set up test environment."""
        PluginRegistry.clear()
        for key in list(os.environ.keys()):
            if key.startswith("MOCK_") or key.startswith("WORKFLOW_"):
                del os.environ[key]

    def teardown_method(self):
        """Clean up after tests."""
        PluginRegistry.clear()
        for key in list(os.environ.keys()):
            if key.startswith("MOCK_") or key.startswith("WORKFLOW_"):
                del os.environ[key]

    def test_complete_plugin_workflow(self):
        """Test complete workflow: discover -> register -> use."""
        # Step 1: Discover plugins (no-op in test environment, but should work)
        TripWire.discover_plugins()

        # Step 2: Manually register a test plugin
        PluginRegistry.register_plugin("workflow-test", MockValidPlugin)

        # Step 3: Get plugin class
        PluginClass = PluginRegistry.get_plugin("workflow-test")

        # Step 4: Create plugin instance with config
        plugin = PluginClass(api_key="workflow-api-key", url="https://workflow.example.com")

        # Step 5: Use plugin with TripWire
        env = TripWire(sources=[plugin], auto_load=True)

        # Step 6: Require variables with validation
        api_key = env.require("MOCK_API_KEY", min_length=5)
        url = env.require("MOCK_URL", format="url")
        loaded = env.require("MOCK_LOADED", type=bool)

        # Verify
        assert api_key == "workflow-api-key"
        assert url == "https://workflow.example.com"
        assert loaded is True

    def test_plugin_config_validation(self):
        """Test plugin config validation in workflow."""
        plugin = MockValidPlugin()

        # Valid config
        valid_config = {"api_key": "test", "url": "https://example.com"}
        assert plugin.validate_config(valid_config) is True

        # Invalid config (missing required keys)
        invalid_config = {"api_key": "test"}  # Missing 'url'
        with pytest.raises(Exception):  # Should raise PluginValidationError
            plugin.validate_config(invalid_config)

    def test_plugin_list_and_select(self):
        """Test listing plugins and selecting one to use."""
        # Register multiple plugins
        PluginRegistry.register_plugin("plugin-a", MockValidPlugin)
        PluginRegistry.register_plugin("plugin-b", MockSimplePlugin)

        # List all plugins
        plugins = PluginRegistry.list_plugins()
        assert len(plugins) >= 2

        # Select plugin by name
        plugin_names = [p.name for p in plugins]
        assert "mock-valid" in plugin_names
        assert "mock-simple" in plugin_names

        # Use selected plugin
        SelectedPlugin = PluginRegistry.get_plugin("plugin-b")
        plugin = SelectedPlugin()
        env = TripWire(sources=[plugin], auto_load=True)

        assert env.require("SIMPLE_TEST") == "true"

    def test_plugin_metadata_access(self):
        """Test accessing plugin metadata."""
        plugin = MockValidPlugin()
        metadata = plugin.metadata

        assert metadata.name == "mock-valid"
        assert metadata.version == "1.0.0"
        assert metadata.author == "TripWire Test Suite"
        assert metadata.description == "A valid mock plugin for testing"
        assert "test" in metadata.tags
        assert "mock" in metadata.tags


class TestPluginErrorHandling:
    """Tests for error handling in plugin integration."""

    def setup_method(self):
        """Set up test environment."""
        PluginRegistry.clear()

    def teardown_method(self):
        """Clean up after tests."""
        PluginRegistry.clear()

    def test_tripwire_with_no_sources_uses_default(self):
        """Test that TripWire without sources uses default dotenv source."""
        # Create TripWire without sources
        env = TripWire(auto_load=False)  # Don't auto-load to avoid file errors

        # Should still work (uses default .env source)
        assert env is not None
        assert hasattr(env, "require")

    def test_plugin_validation_in_registry(self):
        """Test that invalid plugins are rejected by registry."""
        from tests.plugins.fixtures.mock_plugin import MockInvalidPlugin

        with pytest.raises(Exception):  # Should raise PluginValidationError
            PluginRegistry.register_plugin("invalid", MockInvalidPlugin)  # type: ignore[arg-type]

    def test_plugin_not_found_error_message(self):
        """Test that helpful error message is shown for missing plugin."""
        with pytest.raises(Exception) as exc_info:  # Should raise PluginNotFoundError
            PluginRegistry.get_plugin("nonexistent-plugin")

        error_msg = str(exc_info.value)
        assert "not found" in error_msg
        assert "nonexistent-plugin" in error_msg
