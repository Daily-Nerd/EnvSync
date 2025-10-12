"""Unit tests for the TripWire plugin system.

Tests cover:
- Plugin registration and retrieval
- Plugin discovery via entry points
- Plugin validation (API compatibility, metadata, version)
- Plugin sandboxing (security checks)
- Error handling for invalid plugins
"""

from pathlib import Path

import pytest

from tests.plugins.fixtures.mock_plugin import (
    MockDangerousPlugin,
    MockFailingLoadPlugin,
    MockInvalidPlugin,
    MockNoMetadataPlugin,
    MockSimplePlugin,
    MockValidPlugin,
    MockVersionIncompatiblePlugin,
)
from tripwire.core.plugin_system import (
    PluginLoader,
    PluginRegistry,
    PluginSandbox,
    PluginValidator,
)
from tripwire.plugins import PluginMetadata
from tripwire.plugins.errors import (
    PluginLoadError,
    PluginNotFoundError,
    PluginSecurityError,
    PluginValidationError,
    PluginVersionError,
)


class TestPluginMetadata:
    """Tests for PluginMetadata dataclass."""

    def test_valid_metadata_creation(self):
        """Test creating valid plugin metadata."""
        metadata = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin description",
            homepage="https://example.com",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["test", "example"],
        )

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test plugin description"
        assert metadata.homepage == "https://example.com"
        assert metadata.license == "MIT"
        assert metadata.min_tripwire_version == "0.10.0"
        assert metadata.tags == ["test", "example"]

    def test_metadata_with_defaults(self):
        """Test metadata creation with default values."""
        metadata = PluginMetadata(
            name="minimal-plugin",
            version="1.0.0",
            author="Test Author",
            description="Minimal plugin",
        )

        assert metadata.homepage is None
        assert metadata.license is None
        assert metadata.min_tripwire_version == "0.10.0"
        assert metadata.tags == []

    def test_metadata_validation_empty_name(self):
        """Test that empty name raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            PluginMetadata(
                name="",
                version="1.0.0",
                author="Test",
                description="Test",
            )
        assert "name cannot be empty" in str(exc_info.value)

    def test_metadata_validation_empty_version(self):
        """Test that empty version raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            PluginMetadata(
                name="test",
                version="",
                author="Test",
                description="Test",
            )
        assert "version cannot be empty" in str(exc_info.value)

    def test_metadata_validation_invalid_name_format(self):
        """Test that invalid name format raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            PluginMetadata(
                name="test plugin!",  # Spaces and special chars not allowed
                version="1.0.0",
                author="Test",
                description="Test",
            )
        assert "must contain only alphanumeric" in str(exc_info.value)

    def test_metadata_validation_invalid_version_format(self):
        """Test that invalid version format raises validation error."""
        with pytest.raises(PluginValidationError) as exc_info:
            PluginMetadata(
                name="test",
                version="invalid",  # Not semantic versioning
                author="Test",
                description="Test",
            )
        assert "semantic versioning" in str(exc_info.value)

    def test_metadata_immutability(self):
        """Test that metadata is immutable (frozen dataclass)."""
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            author="Test",
            description="Test",
        )

        with pytest.raises(AttributeError):
            metadata.name = "new-name"  # type: ignore[misc]


class TestPluginRegistry:
    """Tests for PluginRegistry singleton."""

    def setup_method(self):
        """Clear registry before each test."""
        PluginRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        PluginRegistry.clear()

    def test_singleton_pattern(self):
        """Test that PluginRegistry is a singleton."""
        registry1 = PluginRegistry()
        registry2 = PluginRegistry()
        assert registry1 is registry2

    def test_register_valid_plugin(self):
        """Test registering a valid plugin."""
        PluginRegistry.register_plugin("mock-valid", MockValidPlugin)
        plugin_class = PluginRegistry.get_plugin("mock-valid")
        assert plugin_class is MockValidPlugin

    def test_register_simple_plugin(self):
        """Test registering a simple plugin (no init params)."""
        PluginRegistry.register_plugin("mock-simple", MockSimplePlugin)
        plugin_class = PluginRegistry.get_plugin("mock-simple")
        assert plugin_class is MockSimplePlugin

    def test_register_duplicate_name_fails(self):
        """Test that registering duplicate plugin name fails."""
        PluginRegistry.register_plugin("test", MockValidPlugin)

        with pytest.raises(PluginValidationError) as exc_info:
            PluginRegistry.register_plugin("test", MockSimplePlugin)
        assert "already registered" in str(exc_info.value)

    def test_register_invalid_plugin_fails(self):
        """Test that registering invalid plugin fails validation."""
        with pytest.raises(PluginValidationError):
            PluginRegistry.register_plugin("invalid", MockInvalidPlugin)  # type: ignore[arg-type]

    def test_register_no_metadata_plugin_fails(self):
        """Test that plugin without metadata property fails validation."""
        with pytest.raises(PluginValidationError) as exc_info:
            PluginRegistry.register_plugin("no-metadata", MockNoMetadataPlugin)  # type: ignore[arg-type]
        assert "metadata" in str(exc_info.value)

    def test_get_nonexistent_plugin_fails(self):
        """Test that getting non-existent plugin raises error."""
        with pytest.raises(PluginNotFoundError) as exc_info:
            PluginRegistry.get_plugin("nonexistent")
        assert "not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_list_plugins_empty(self):
        """Test listing plugins when registry is empty."""
        plugins = PluginRegistry.list_plugins()
        assert plugins == []

    def test_list_plugins_with_registered_plugins(self):
        """Test listing registered plugins."""
        PluginRegistry.register_plugin("simple", MockSimplePlugin)
        PluginRegistry.register_plugin("valid", MockValidPlugin)

        plugins = PluginRegistry.list_plugins()
        assert len(plugins) == 2

        plugin_names = {p.name for p in plugins}
        assert "mock-simple" in plugin_names
        assert "mock-valid" in plugin_names

    def test_clear_registry(self):
        """Test clearing the registry."""
        PluginRegistry.register_plugin("test", MockSimplePlugin)
        assert len(PluginRegistry.list_plugins()) == 1

        PluginRegistry.clear()
        assert len(PluginRegistry.list_plugins()) == 0


class TestPluginLoader:
    """Tests for PluginLoader."""

    def test_loader_initialization(self):
        """Test creating a PluginLoader instance."""
        loader = PluginLoader()
        assert loader is not None

    def test_load_from_entry_points_no_plugins(self):
        """Test loading from entry points when no plugins are installed."""
        loader = PluginLoader()
        plugins = loader.load_from_entry_points()

        # Should return empty dict (no plugins registered in test environment)
        assert isinstance(plugins, dict)

    def test_load_from_path_nonexistent_file(self):
        """Test loading from non-existent file path fails."""
        loader = PluginLoader()

        with pytest.raises(PluginLoadError) as exc_info:
            loader.load_from_path(Path("/nonexistent/plugin.py"))
        assert "not found" in str(exc_info.value)

    def test_validate_plugin_valid(self):
        """Test validating a valid plugin."""
        loader = PluginLoader()
        is_valid = loader.validate_plugin(MockValidPlugin)
        assert is_valid is True

    def test_validate_plugin_invalid(self):
        """Test validating an invalid plugin fails."""
        loader = PluginLoader()

        with pytest.raises(PluginValidationError):
            loader.validate_plugin(MockInvalidPlugin)  # type: ignore[arg-type]


class TestPluginValidator:
    """Tests for PluginValidator."""

    def test_validate_valid_plugin(self):
        """Test validating a plugin with all required methods."""
        validator = PluginValidator()
        is_valid = validator.validate_plugin(MockValidPlugin)
        assert is_valid is True

    def test_validate_simple_plugin(self):
        """Test validating a simple plugin (no init params)."""
        validator = PluginValidator()
        is_valid = validator.validate_plugin(MockSimplePlugin)
        assert is_valid is True

    def test_validate_non_class_fails(self):
        """Test that validating a non-class fails."""
        validator = PluginValidator()

        def not_a_class():
            pass

        with pytest.raises(PluginValidationError) as exc_info:
            validator.validate_plugin(not_a_class)  # type: ignore[arg-type]
        assert "must be a class" in str(exc_info.value)

    def test_validate_missing_methods_fails(self):
        """Test that plugin missing required methods fails validation."""
        validator = PluginValidator()

        with pytest.raises(PluginValidationError) as exc_info:
            validator.validate_plugin(MockInvalidPlugin)  # type: ignore[arg-type]

        error_msg = str(exc_info.value)
        assert "metadata" in error_msg
        assert "load" in error_msg
        assert "validate_config" in error_msg

    def test_validate_no_metadata_fails(self):
        """Test that plugin without metadata fails validation."""
        validator = PluginValidator()

        with pytest.raises(PluginValidationError) as exc_info:
            validator.validate_plugin(MockNoMetadataPlugin)  # type: ignore[arg-type]
        assert "metadata" in str(exc_info.value)

    def test_check_version_compatibility_compatible(self):
        """Test version compatibility check with compatible version."""
        validator = PluginValidator()

        # Should not raise error (0.10.0 is compatible with 0.10.0)
        is_compatible = validator.check_version_compatibility("test-plugin", "1.0.0", "0.10.0")
        assert is_compatible is True

    def test_check_version_compatibility_incompatible(self):
        """Test version compatibility check with incompatible version."""
        validator = PluginValidator()

        with pytest.raises(PluginVersionError) as exc_info:
            validator.check_version_compatibility("test-plugin", "1.0.0", "99.0.0")  # Requires future version
        assert "99.0.0" in str(exc_info.value)

    def test_validate_metadata_valid(self):
        """Test validating valid metadata."""
        validator = PluginValidator()
        metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            author="Test",
            description="Test",
        )
        is_valid = validator.validate_metadata(metadata)
        assert is_valid is True


class TestPluginSandbox:
    """Tests for PluginSandbox security checks."""

    def test_sandbox_initialization(self):
        """Test creating a PluginSandbox instance."""
        sandbox = PluginSandbox()
        assert sandbox is not None

    def test_validate_safe_operations_valid_plugin(self):
        """Test that valid plugin passes security checks."""
        sandbox = PluginSandbox()
        plugin = MockValidPlugin()
        is_safe = sandbox.validate_safe_operations(plugin)
        assert is_safe is True

    def test_validate_safe_operations_simple_plugin(self):
        """Test that simple plugin passes security checks."""
        sandbox = PluginSandbox()
        plugin = MockSimplePlugin()
        is_safe = sandbox.validate_safe_operations(plugin)
        assert is_safe is True

    def test_validate_safe_operations_dangerous_plugin(self):
        """Test that dangerous plugin fails security checks."""
        sandbox = PluginSandbox()
        plugin = MockDangerousPlugin()

        with pytest.raises(PluginSecurityError) as exc_info:
            sandbox.validate_safe_operations(plugin)
        assert "subprocess" in str(exc_info.value)

    def test_restrict_permissions(self):
        """Test restrict_permissions method (placeholder)."""
        sandbox = PluginSandbox()
        plugin = MockValidPlugin()

        # Currently a placeholder - should not raise error
        sandbox.restrict_permissions(plugin)


class TestPluginIntegration:
    """Integration tests combining multiple plugin system components."""

    def setup_method(self):
        """Clear registry before each test."""
        PluginRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        PluginRegistry.clear()

    def test_register_and_use_plugin(self):
        """Test registering a plugin and using it."""
        # Register plugin
        PluginRegistry.register_plugin("test", MockValidPlugin)

        # Retrieve plugin class
        PluginClass = PluginRegistry.get_plugin("test")

        # Instantiate plugin
        plugin = PluginClass(api_key="test-key", url="https://example.com")

        # Use plugin
        env_vars = plugin.load()
        assert env_vars["MOCK_API_KEY"] == "test-key"
        assert env_vars["MOCK_URL"] == "https://example.com"

    def test_plugin_validation_during_registration(self):
        """Test that plugins are validated during registration."""
        # Valid plugin should register successfully
        PluginRegistry.register_plugin("valid", MockValidPlugin)

        # Invalid plugin should fail
        with pytest.raises(PluginValidationError):
            PluginRegistry.register_plugin("invalid", MockInvalidPlugin)  # type: ignore[arg-type]

    def test_plugin_load_error_handling(self):
        """Test handling of plugin load errors."""
        plugin = MockFailingLoadPlugin()

        with pytest.raises(Exception):  # Should raise PluginAPIError
            plugin.load()

    def test_multiple_plugins_registration(self):
        """Test registering and retrieving multiple plugins."""
        PluginRegistry.register_plugin("plugin1", MockValidPlugin)
        PluginRegistry.register_plugin("plugin2", MockSimplePlugin)

        plugins = PluginRegistry.list_plugins()
        assert len(plugins) == 2

        # Verify we can retrieve both
        plugin1 = PluginRegistry.get_plugin("plugin1")
        plugin2 = PluginRegistry.get_plugin("plugin2")

        assert plugin1 is MockValidPlugin
        assert plugin2 is MockSimplePlugin
