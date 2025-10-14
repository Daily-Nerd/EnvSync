"""Tests for bundled plugin registry system."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tripwire.plugins.registry import PluginRegistryClient


class TestBundledRegistry:
    """Test bundled registry functionality."""

    def test_bundled_registry_exists(self):
        """Test that bundled registry file exists in package."""
        client = PluginRegistryClient()
        assert client.BUNDLED_REGISTRY_PATH.exists(), (
            f"Bundled registry not found at {client.BUNDLED_REGISTRY_PATH}. "
            "This indicates package corruption or incomplete build."
        )

    def test_bundled_registry_valid_json(self):
        """Test that bundled registry is valid JSON."""
        client = PluginRegistryClient()
        with open(client.BUNDLED_REGISTRY_PATH, "r") as f:
            registry_data = json.load(f)

        # Validate structure
        assert "version" in registry_data
        assert "plugins" in registry_data
        assert isinstance(registry_data["plugins"], dict)

    def test_bundled_registry_has_official_plugins(self):
        """Test that bundled registry contains all 4 official plugins."""
        client = PluginRegistryClient()
        with open(client.BUNDLED_REGISTRY_PATH, "r") as f:
            registry_data = json.load(f)

        plugins = registry_data["plugins"]

        # Check all 4 official plugins are present
        expected_plugins = ["vault", "aws-secrets", "azure-keyvault", "remote-config"]
        for plugin_id in expected_plugins:
            assert plugin_id in plugins, f"Official plugin '{plugin_id}' missing from bundled registry"

    def test_bundled_registry_plugins_have_builtin_urls(self):
        """Test that bundled plugins use builtin:// URLs."""
        client = PluginRegistryClient()
        with open(client.BUNDLED_REGISTRY_PATH, "r") as f:
            registry_data = json.load(f)

        plugins = registry_data["plugins"]

        for plugin_id, plugin_data in plugins.items():
            versions = plugin_data.get("versions", {})
            for version_id, version_data in versions.items():
                download_url = version_data.get("download_url", "")
                assert download_url.startswith(
                    "builtin://"
                ), f"Plugin '{plugin_id}' version '{version_id}' does not use builtin:// URL"

    def test_bundled_registry_plugins_marked_as_official(self):
        """Test that bundled plugins are marked as official."""
        client = PluginRegistryClient()
        with open(client.BUNDLED_REGISTRY_PATH, "r") as f:
            registry_data = json.load(f)

        plugins = registry_data["plugins"]

        for plugin_id, plugin_data in plugins.items():
            assert plugin_data.get("official") is True, f"Plugin '{plugin_id}' not marked as official"
            assert plugin_data.get("bundled") is True, f"Plugin '{plugin_id}' not marked as bundled"

    def test_load_bundled_registry(self):
        """Test loading bundled registry."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        assert registry is not None
        assert registry.version is not None
        assert len(registry.plugins) >= 4  # At least 4 official plugins

    def test_bundled_registry_metadata_complete(self):
        """Test that bundled registry has complete metadata for all plugins."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        required_fields = ["name", "display_name", "description", "author", "license"]

        for plugin_id, plugin_entry in registry.plugins.items():
            for field in required_fields:
                value = getattr(plugin_entry, field, None)
                assert value, f"Plugin '{plugin_id}' missing required field '{field}'"

    def test_bundled_registry_versions_valid(self):
        """Test that bundled registry versions have valid metadata."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        for plugin_id, plugin_entry in registry.plugins.items():
            assert plugin_entry.latest_version, f"Plugin '{plugin_id}' missing latest_version"
            assert plugin_entry.versions, f"Plugin '{plugin_id}' has no versions"

            # Check latest version exists in versions dict
            latest_version_info = plugin_entry.get_version()
            assert latest_version_info is not None, f"Plugin '{plugin_id}' latest version not in versions dict"


class TestBundledRegistryFallback:
    """Test bundled registry fallback behavior."""

    def test_fallback_to_bundled_when_remote_fails(self, tmp_path):
        """Test that bundled registry is used when remote fetch fails."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Mock network failure
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            registry = client.fetch_registry(use_cache=False)

        # Should fall back to bundled registry
        assert registry is not None
        assert len(registry.plugins) >= 4  # Official plugins

    def test_fallback_priority_remote_cache_bundled(self, tmp_path):
        """Test fallback priority: Remote → Cache → Bundled."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Create cache with custom data
        cache_data = {
            "version": "1.0.0",
            "updated_at": "2025-01-01T00:00:00Z",
            "plugins": {
                "test-plugin": {
                    "name": "test-plugin",
                    "display_name": "Test Plugin",
                    "description": "Test plugin from cache",
                    "author": "Test Author",
                    "author_email": "test@example.com",
                    "homepage": "https://example.com",
                    "repository": "https://example.com",
                    "license": "MIT",
                    "versions": {
                        "1.0.0": {
                            "version": "1.0.0",
                            "release_date": "2025-01-01",
                            "min_tripwire_version": "0.10.0",
                            "download_url": "https://example.com/plugin.tar.gz",
                        }
                    },
                    "latest_version": "1.0.0",
                }
            },
        }

        with open(client.CACHE_FILE, "w") as f:
            json.dump(cache_data, f)

        # Mock remote failure
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            registry = client.fetch_registry(use_cache=True)

        # Should use cache (priority 2)
        assert "test-plugin" in registry.plugins

    def test_bundled_registry_always_available(self, tmp_path):
        """Test that bundled registry is always available as last resort."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # No cache file, no remote access
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            registry = client.fetch_registry(use_cache=False)

        # Should still work via bundled registry
        assert registry is not None
        assert len(registry.plugins) >= 4

    def test_bundled_registry_offline_mode(self, tmp_path):
        """Test that plugin system works completely offline."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Ensure no cache exists
        if client.CACHE_FILE.exists():
            client.CACHE_FILE.unlink()

        # Block all network access
        with patch("urllib.request.urlopen", side_effect=Exception("Offline mode")):
            registry = client.fetch_registry(use_cache=False)

        # Should work with bundled registry
        assert registry is not None

        # Should have official plugins
        assert "vault" in registry.plugins
        assert "aws-secrets" in registry.plugins
        assert "azure-keyvault" in registry.plugins
        assert "remote-config" in registry.plugins

    def test_bundled_registry_missing_raises_error(self, tmp_path):
        """Test that missing bundled registry raises clear error."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Point to non-existent bundled registry
        client.BUNDLED_REGISTRY_PATH = tmp_path / "nonexistent.json"

        # Block network and ensure no cache
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            with pytest.raises(RuntimeError, match="Failed to fetch plugin registry"):
                client.fetch_registry(use_cache=False)


class TestBundledRegistryPluginInfo:
    """Test plugin information in bundled registry."""

    def test_vault_plugin_metadata(self):
        """Test HashiCorp Vault plugin metadata."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        vault = registry.get_plugin("vault")
        assert vault is not None
        assert vault.name == "vault"
        assert vault.display_name == "HashiCorp Vault"
        assert "vault" in vault.description.lower()
        assert vault.author == "TripWire Team"
        assert vault.license == "MIT"
        assert "vault" in vault.tags
        assert "hashicorp" in vault.tags

    def test_aws_secrets_plugin_metadata(self):
        """Test AWS Secrets Manager plugin metadata."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        aws = registry.get_plugin("aws-secrets")
        assert aws is not None
        assert aws.name == "aws-secrets"
        assert aws.display_name == "AWS Secrets Manager"
        assert "aws" in aws.description.lower()
        assert aws.author == "TripWire Team"
        assert aws.license == "MIT"
        assert "aws" in aws.tags

    def test_azure_keyvault_plugin_metadata(self):
        """Test Azure Key Vault plugin metadata."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        azure = registry.get_plugin("azure-keyvault")
        assert azure is not None
        assert azure.name == "azure-keyvault"
        assert azure.display_name == "Azure Key Vault"
        assert "azure" in azure.description.lower()
        assert azure.author == "TripWire Team"
        assert azure.license == "MIT"
        assert "azure" in azure.tags

    def test_remote_config_plugin_metadata(self):
        """Test Remote HTTP Config plugin metadata."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        remote = registry.get_plugin("remote-config")
        assert remote is not None
        assert remote.name == "remote-config"
        assert remote.display_name == "Remote HTTP Config"
        assert "http" in remote.description.lower() or "api" in remote.description.lower()
        assert remote.author == "TripWire Team"
        assert remote.license == "MIT"
        assert "http" in remote.tags or "api" in remote.tags

    def test_plugin_search_works_with_bundled(self):
        """Test search functionality works with bundled registry."""
        client = PluginRegistryClient()
        registry = client._load_bundled_registry()

        # Search for various terms
        vault_results = registry.search("vault")
        assert len(vault_results) > 0
        assert any(p.name == "vault" for p in vault_results)

        aws_results = registry.search("aws")
        assert len(aws_results) > 0
        assert any(p.name == "aws-secrets" for p in aws_results)

        secrets_results = registry.search("secrets")
        assert len(secrets_results) >= 3  # vault, aws-secrets, azure-keyvault

        cloud_results = registry.search("cloud")
        assert len(cloud_results) >= 3  # All cloud providers
