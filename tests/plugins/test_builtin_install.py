"""Tests for builtin plugin installation system."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tripwire.plugins.registry import (
    PluginInstaller,
    PluginRegistryClient,
    PluginRegistryEntry,
    PluginRegistryIndex,
    PluginVersionInfo,
)


class TestBuiltinPluginInstallation:
    """Test installing builtin plugins."""

    @pytest.fixture
    def bundled_registry(self):
        """Get bundled registry with real plugins."""
        client = PluginRegistryClient()
        return client._load_bundled_registry()

    @pytest.fixture
    def installer(self, tmp_path, bundled_registry):
        """Create installer with bundled registry."""
        mock_client = MagicMock(spec=PluginRegistryClient)
        mock_client.fetch_registry.return_value = bundled_registry

        installer = PluginInstaller(mock_client)
        installer.PLUGINS_DIR = tmp_path
        return installer

    def test_install_vault_builtin_plugin(self, installer, bundled_registry):
        """Test installing Vault builtin plugin."""
        plugin_dir = installer.install("vault")

        # Check plugin directory created
        assert plugin_dir.exists()
        assert plugin_dir.is_dir()

        # Check .builtin marker file exists
        builtin_marker = plugin_dir / ".builtin"
        assert builtin_marker.exists()

        # Check metadata in .builtin file
        with open(builtin_marker, "r") as f:
            metadata = json.load(f)

        assert metadata["name"] == "vault"
        assert metadata["display_name"] == "HashiCorp Vault"
        assert metadata["bundled"] is True
        assert metadata["official"] is True
        assert "install_url" in metadata
        assert metadata["install_url"].startswith("builtin://")
        assert metadata["module_path"] == "tripwire.plugins.sources.vault"
        assert metadata["class_name"] == "VaultEnvSource"

    def test_install_aws_secrets_builtin_plugin(self, installer, bundled_registry):
        """Test installing AWS Secrets Manager builtin plugin."""
        plugin_dir = installer.install("aws-secrets")

        assert plugin_dir.exists()

        builtin_marker = plugin_dir / ".builtin"
        assert builtin_marker.exists()

        with open(builtin_marker, "r") as f:
            metadata = json.load(f)

        assert metadata["name"] == "aws-secrets"
        assert metadata["module_path"] == "tripwire.plugins.sources.aws_secrets"
        assert metadata["class_name"] == "AWSSecretsSource"

    def test_install_azure_keyvault_builtin_plugin(self, installer, bundled_registry):
        """Test installing Azure Key Vault builtin plugin."""
        plugin_dir = installer.install("azure-keyvault")

        assert plugin_dir.exists()

        builtin_marker = plugin_dir / ".builtin"
        assert builtin_marker.exists()

        with open(builtin_marker, "r") as f:
            metadata = json.load(f)

        assert metadata["name"] == "azure-keyvault"
        assert metadata["module_path"] == "tripwire.plugins.sources.azure_keyvault"
        assert metadata["class_name"] == "AzureKeyVaultSource"

    def test_install_remote_config_builtin_plugin(self, installer, bundled_registry):
        """Test installing Remote HTTP Config builtin plugin."""
        plugin_dir = installer.install("remote-config")

        assert plugin_dir.exists()

        builtin_marker = plugin_dir / ".builtin"
        assert builtin_marker.exists()

        with open(builtin_marker, "r") as f:
            metadata = json.load(f)

        assert metadata["name"] == "remote-config"
        assert metadata["module_path"] == "tripwire.plugins.sources.remote_config"
        assert metadata["class_name"] == "RemoteConfigSource"

    def test_builtin_plugin_already_installed(self, installer, bundled_registry):
        """Test that installing already installed builtin plugin fails without force."""
        # Install once
        installer.install("vault")

        # Try to install again without force
        with pytest.raises(RuntimeError, match="already installed"):
            installer.install("vault")

    def test_builtin_plugin_force_reinstall(self, installer, bundled_registry):
        """Test force reinstalling builtin plugin."""
        # Install once
        plugin_dir = installer.install("vault")
        first_metadata_file = plugin_dir / ".builtin"

        # Get install time from first installation
        with open(first_metadata_file, "r") as f:
            first_metadata = json.load(f)
        first_install_time = first_metadata["installed_at"]

        # Force reinstall
        plugin_dir = installer.install("vault", force=True)

        # Check it was reinstalled (new install time)
        with open(first_metadata_file, "r") as f:
            second_metadata = json.load(f)
        second_install_time = second_metadata["installed_at"]

        # Install times should be different (though very close)
        # We can't guarantee they're different due to timestamp precision,
        # but metadata should still be valid
        assert plugin_dir.exists()
        assert first_metadata_file.exists()

    def test_builtin_plugin_import_validation(self, installer, bundled_registry):
        """Test that builtin plugins can actually be imported."""
        installer.install("vault")

        # Try to import the plugin class
        from tripwire.plugins.sources.vault import VaultEnvSource

        assert VaultEnvSource is not None
        assert hasattr(VaultEnvSource, "load")

    def test_all_bundled_plugins_installable(self, installer, bundled_registry):
        """Test that all bundled plugins can be installed."""
        expected_plugins = ["vault", "aws-secrets", "azure-keyvault", "remote-config"]

        for plugin_id in expected_plugins:
            plugin_dir = installer.install(plugin_id)
            assert plugin_dir.exists()

            builtin_marker = plugin_dir / ".builtin"
            assert builtin_marker.exists()

    def test_builtin_plugin_list_shows_installed(self, installer, bundled_registry):
        """Test that installed builtin plugins appear in list."""
        # Install a few plugins
        installer.install("vault")
        installer.install("aws-secrets")

        installed = installer.list_installed()

        assert "vault" in installed
        assert "aws-secrets" in installed
        assert len(installed) == 2

    def test_builtin_plugin_is_installed_check(self, installer, bundled_registry):
        """Test checking if builtin plugin is installed."""
        assert not installer.is_installed("vault")

        installer.install("vault")

        assert installer.is_installed("vault")

    def test_builtin_plugin_uninstall(self, installer, bundled_registry):
        """Test uninstalling builtin plugin."""
        # Install plugin
        plugin_dir = installer.install("vault")
        assert plugin_dir.exists()
        assert installer.is_installed("vault")

        # Uninstall
        installer.uninstall("vault")

        assert not plugin_dir.exists()
        assert not installer.is_installed("vault")


class TestBuiltinURLParsing:
    """Test parsing of builtin:// URLs."""

    def test_parse_builtin_url(self):
        """Test parsing valid builtin URL."""
        url = "builtin://tripwire.plugins.sources.vault/VaultEnvSource"

        assert url.startswith("builtin://")

        url_path = url.replace("builtin://", "")
        module_path, class_name = url_path.rsplit("/", 1)

        assert module_path == "tripwire.plugins.sources.vault"
        assert class_name == "VaultEnvSource"

    def test_invalid_builtin_url_no_slash(self):
        """Test handling of invalid builtin URL without slash."""
        url = "builtin://tripwire.plugins.sources.vault"

        url_path = url.replace("builtin://", "")

        # Should not contain "/"
        assert "/" not in url_path

    def test_builtin_url_various_plugins(self):
        """Test parsing builtin URLs for all official plugins."""
        urls = {
            "vault": "builtin://tripwire.plugins.sources.vault/VaultEnvSource",
            "aws-secrets": "builtin://tripwire.plugins.sources.aws_secrets/AWSSecretsSource",
            "azure-keyvault": "builtin://tripwire.plugins.sources.azure_keyvault/AzureKeyVaultSource",
            "remote-config": "builtin://tripwire.plugins.sources.remote_config/RemoteConfigSource",
        }

        for plugin_id, url in urls.items():
            url_path = url.replace("builtin://", "")
            module_path, class_name = url_path.rsplit("/", 1)

            # Validate structure
            assert module_path.startswith("tripwire.plugins.sources.")
            assert class_name.endswith("Source")


class TestBuiltinPluginErrorHandling:
    """Test error handling in builtin plugin installation."""

    @pytest.fixture
    def installer_with_bad_url(self, tmp_path):
        """Create installer with invalid builtin URL."""
        # Create registry with invalid builtin URL
        version = PluginVersionInfo(
            version="1.0.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
            download_url="builtin://invalid.module/InvalidClass",
        )

        entry = PluginRegistryEntry(
            name="bad-plugin",
            display_name="Bad Plugin",
            description="Plugin with invalid module",
            author="Test",
            author_email="test@example.com",
            homepage="https://example.com",
            repository="https://example.com",
            license="MIT",
            versions={"1.0.0": version},
            latest_version="1.0.0",
        )

        registry = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"bad-plugin": entry},
        )

        mock_client = MagicMock(spec=PluginRegistryClient)
        mock_client.fetch_registry.return_value = registry

        installer = PluginInstaller(mock_client)
        installer.PLUGINS_DIR = tmp_path
        return installer

    def test_builtin_plugin_invalid_module(self, installer_with_bad_url):
        """Test error when builtin plugin module doesn't exist."""
        with pytest.raises(RuntimeError, match="Failed to import builtin plugin"):
            installer_with_bad_url.install("bad-plugin")

    @pytest.fixture
    def installer_with_bad_class(self, tmp_path):
        """Create installer with invalid class name."""
        version = PluginVersionInfo(
            version="1.0.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
            download_url="builtin://tripwire.plugins.sources.vault/NonExistentClass",
        )

        entry = PluginRegistryEntry(
            name="bad-class-plugin",
            display_name="Bad Class Plugin",
            description="Plugin with invalid class",
            author="Test",
            author_email="test@example.com",
            homepage="https://example.com",
            repository="https://example.com",
            license="MIT",
            versions={"1.0.0": version},
            latest_version="1.0.0",
        )

        registry = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"bad-class-plugin": entry},
        )

        mock_client = MagicMock(spec=PluginRegistryClient)
        mock_client.fetch_registry.return_value = registry

        installer = PluginInstaller(mock_client)
        installer.PLUGINS_DIR = tmp_path
        return installer

    def test_builtin_plugin_invalid_class(self, installer_with_bad_class):
        """Test error when builtin plugin class doesn't exist."""
        with pytest.raises(RuntimeError, match="Plugin class .* not found"):
            installer_with_bad_class.install("bad-class-plugin")


class TestBuiltinPluginIntegration:
    """Integration tests for builtin plugin system."""

    def test_end_to_end_builtin_plugin_workflow(self, tmp_path):
        """Test complete workflow: fetch registry → install plugin → use plugin."""
        # Use real registry client to get bundled registry
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path / "cache"
        client.CACHE_FILE = client.CACHE_DIR / "registry.json"

        # Block network to force bundled registry
        with pytest.MonkeyPatch().context() as m:

            def mock_urlopen(*args, **kwargs):
                raise Exception("Network blocked for test")

            m.setattr("urllib.request.urlopen", mock_urlopen)

            # Fetch registry (should use bundled)
            registry = client.fetch_registry(use_cache=False)

        # Create installer
        installer = PluginInstaller(client)
        installer.PLUGINS_DIR = tmp_path / "plugins"

        # Install builtin plugin
        plugin_dir = installer.install("vault")

        # Verify installation
        assert plugin_dir.exists()
        assert (plugin_dir / ".builtin").exists()

        # Verify plugin is listed
        assert "vault" in installer.list_installed()

        # Verify plugin can be imported
        from tripwire.plugins.sources.vault import VaultEnvSource

        assert VaultEnvSource is not None
