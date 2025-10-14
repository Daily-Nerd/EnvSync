"""Tests for plugin registry and installation system."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from tripwire.plugins.registry import (
    PluginInstaller,
    PluginRegistryClient,
    PluginRegistryEntry,
    PluginRegistryIndex,
    PluginVersionInfo,
)


class TestPluginVersionInfo:
    """Test PluginVersionInfo dataclass."""

    def test_create_version_info(self):
        """Test creating version info."""
        version = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
            download_url="https://example.com/plugin.tar.gz",
            checksum="sha256:abc123",
            downloads=100,
        )

        assert version.version == "0.1.0"
        assert version.release_date == "2025-01-01"
        assert version.min_tripwire_version == "0.10.0"
        assert version.downloads == 100

    def test_version_info_requires_version(self):
        """Test that version is required."""
        with pytest.raises(ValueError, match="version cannot be empty"):
            PluginVersionInfo(
                version="",
                release_date="2025-01-01",
                min_tripwire_version="0.10.0",
            )

    def test_version_info_requires_min_tripwire_version(self):
        """Test that min_tripwire_version is required."""
        with pytest.raises(ValueError, match="min_tripwire_version cannot be empty"):
            PluginVersionInfo(
                version="0.1.0",
                release_date="2025-01-01",
                min_tripwire_version="",
            )


class TestPluginRegistryEntry:
    """Test PluginRegistryEntry dataclass."""

    def test_create_registry_entry(self):
        """Test creating registry entry."""
        version = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
        )

        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="HashiCorp Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            tags=["vault", "secrets"],
            versions={"0.1.0": version},
            latest_version="0.1.0",
            total_downloads=100,
        )

        assert entry.name == "tripwire-vault"
        assert entry.display_name == "HashiCorp Vault"
        assert entry.latest_version == "0.1.0"
        assert len(entry.versions) == 1

    def test_get_version_latest(self):
        """Test getting latest version."""
        version = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
        )

        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="HashiCorp Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            versions={"0.1.0": version},
            latest_version="0.1.0",
        )

        # Get latest version (no version specified)
        latest = entry.get_version()
        assert latest is not None
        assert latest.version == "0.1.0"

    def test_get_version_specific(self):
        """Test getting specific version."""
        v1 = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
        )
        v2 = PluginVersionInfo(
            version="0.2.0",
            release_date="2025-02-01",
            min_tripwire_version="0.10.0",
        )

        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="HashiCorp Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            versions={"0.1.0": v1, "0.2.0": v2},
            latest_version="0.2.0",
        )

        # Get specific version
        specific = entry.get_version("0.1.0")
        assert specific is not None
        assert specific.version == "0.1.0"

    def test_get_version_not_found(self):
        """Test getting non-existent version."""
        version = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
        )

        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="HashiCorp Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            versions={"0.1.0": version},
            latest_version="0.1.0",
        )

        # Get non-existent version
        missing = entry.get_version("0.9.0")
        assert missing is None

    def test_matches_search_by_name(self):
        """Test search matching by name."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )

        assert entry.matches_search("vault")
        assert entry.matches_search("VAULT")  # Case insensitive
        assert entry.matches_search("tripwire")

    def test_matches_search_by_description(self):
        """Test search matching by description."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Integrate with HashiCorp Vault secrets",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )

        assert entry.matches_search("secrets")
        assert entry.matches_search("integrate")

    def test_matches_search_by_tags(self):
        """Test search matching by tags."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            tags=["hashicorp", "secrets", "kv"],
        )

        assert entry.matches_search("hashicorp")
        assert entry.matches_search("secrets")
        assert entry.matches_search("kv")

    def test_matches_search_no_match(self):
        """Test search with no match."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            tags=["hashicorp"],
        )

        assert not entry.matches_search("aws")
        assert not entry.matches_search("azure")


class TestPluginRegistryIndex:
    """Test PluginRegistryIndex dataclass."""

    def test_create_registry_index(self):
        """Test creating registry index."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )

        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"vault": entry},
        )

        assert index.version == "1.0.0"
        assert len(index.plugins) == 1

    def test_search_empty_query_returns_all(self):
        """Test search with empty query returns all plugins."""
        entry1 = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )
        entry2 = PluginRegistryEntry(
            name="tripwire-aws",
            display_name="AWS Secrets",
            description="AWS integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/aws",
            repository="https://github.com/tripwire-plugins/aws",
            license="MIT",
        )

        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"vault": entry1, "aws": entry2},
        )

        results = index.search("")
        assert len(results) == 2

    def test_search_returns_matches(self):
        """Test search returns matching plugins."""
        entry1 = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )
        entry2 = PluginRegistryEntry(
            name="tripwire-aws",
            display_name="AWS Secrets",
            description="AWS integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/aws",
            repository="https://github.com/tripwire-plugins/aws",
            license="MIT",
        )

        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"vault": entry1, "aws": entry2},
        )

        results = index.search("vault")
        assert len(results) == 1
        assert results[0].name == "tripwire-vault"

    def test_search_sorts_by_relevance(self):
        """Test search sorts by relevance (name > display > description)."""
        entry1 = PluginRegistryEntry(
            name="tripwire-secrets",
            display_name="Secrets Manager",
            description="Generic secrets management",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/secrets",
            repository="https://github.com/tripwire-plugins/secrets",
            license="MIT",
        )
        entry2 = PluginRegistryEntry(
            name="tripwire-aws",
            display_name="AWS Secrets",
            description="AWS integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/aws",
            repository="https://github.com/tripwire-plugins/aws",
            license="MIT",
        )
        entry3 = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Store secrets in Vault",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )

        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"secrets": entry1, "aws": entry2, "vault": entry3},
        )

        # Search for "secrets" - entry1 has it in name, entry2 in display, entry3 in description
        results = index.search("secrets")
        assert len(results) == 3
        assert results[0].name == "tripwire-secrets"  # Name match (highest score)
        assert results[1].name == "tripwire-aws"  # Display name match
        assert results[2].name == "tripwire-vault"  # Description match

    def test_get_plugin_found(self):
        """Test getting plugin by ID."""
        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
        )

        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"vault": entry},
        )

        result = index.get_plugin("vault")
        assert result is not None
        assert result.name == "tripwire-vault"

    def test_get_plugin_not_found(self):
        """Test getting non-existent plugin."""
        index = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={},
        )

        result = index.get_plugin("nonexistent")
        assert result is None


class TestPluginRegistryClient:
    """Test PluginRegistryClient."""

    @pytest.fixture
    def mock_registry_data(self):
        """Create mock registry data."""
        return {
            "version": "1.0.0",
            "updated_at": "2025-01-01T00:00:00Z",
            "plugins": {
                "vault": {
                    "name": "tripwire-vault",
                    "display_name": "HashiCorp Vault",
                    "description": "HashiCorp Vault integration",
                    "author": "TripWire Team",
                    "author_email": "team@tripwire.dev",
                    "homepage": "https://github.com/tripwire-plugins/vault",
                    "repository": "https://github.com/tripwire-plugins/vault",
                    "license": "MIT",
                    "tags": ["vault", "hashicorp"],
                    "versions": {
                        "0.1.0": {
                            "version": "0.1.0",
                            "release_date": "2025-01-01",
                            "min_tripwire_version": "0.10.0",
                            "download_url": "https://example.com/vault-0.1.0.tar.gz",
                            "checksum": "sha256:abc123",
                            "downloads": 100,
                        }
                    },
                    "latest_version": "0.1.0",
                    "total_downloads": 100,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                }
            },
        }

    def test_fetch_registry_from_remote(self, mock_registry_data, tmp_path):
        """Test fetching registry from remote."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Mock URL fetch
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(mock_registry_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            registry = client.fetch_registry(use_cache=False)

        assert registry.version == "1.0.0"
        assert len(registry.plugins) == 1
        assert "vault" in registry.plugins

    def test_fetch_registry_from_cache(self, mock_registry_data, tmp_path):
        """Test fetching registry from cache."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Write cache file
        with open(client.CACHE_FILE, "w") as f:
            json.dump(mock_registry_data, f)

        registry = client.fetch_registry(use_cache=True)

        assert registry.version == "1.0.0"
        assert len(registry.plugins) == 1

    def test_fetch_registry_fallback_to_cache_on_network_error(self, mock_registry_data, tmp_path):
        """Test fallback to cache on network error."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Write cache file
        with open(client.CACHE_FILE, "w") as f:
            json.dump(mock_registry_data, f)

        # Mock network error
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            registry = client.fetch_registry(use_cache=False)

        # Should fall back to cache
        assert registry.version == "1.0.0"
        assert len(registry.plugins) == 1

    def test_fetch_registry_falls_back_to_bundled(self, tmp_path):
        """Test fetch falls back to bundled registry when network fails."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Mock network error
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            registry = client.fetch_registry(use_cache=False)

        # Should fall back to bundled registry (4 official plugins)
        assert registry.version == "1.0.0"
        assert len(registry.plugins) >= 4  # At least the 4 official plugins
        assert "vault" in registry.plugins
        assert "aws-secrets" in registry.plugins
        assert "azure-keyvault" in registry.plugins
        assert "remote-config" in registry.plugins

    def test_clear_cache(self, tmp_path):
        """Test clearing cache."""
        client = PluginRegistryClient()
        client.CACHE_DIR = tmp_path
        client.CACHE_FILE = tmp_path / "registry.json"

        # Create cache file
        client.CACHE_FILE.write_text("{}")

        assert client.CACHE_FILE.exists()

        client.clear_cache()

        assert not client.CACHE_FILE.exists()


class TestPluginInstaller:
    """Test PluginInstaller."""

    @pytest.fixture
    def mock_registry_client(self, mock_registry):
        """Create mock registry client."""
        client = MagicMock(spec=PluginRegistryClient)
        client.fetch_registry.return_value = mock_registry
        return client

    @pytest.fixture
    def mock_registry(self):
        """Create mock registry."""
        version = PluginVersionInfo(
            version="0.1.0",
            release_date="2025-01-01",
            min_tripwire_version="0.10.0",
            download_url="https://example.com/vault-0.1.0.tar.gz",
            checksum="sha256:abc123",
        )

        entry = PluginRegistryEntry(
            name="tripwire-vault",
            display_name="HashiCorp Vault",
            description="Vault integration",
            author="TripWire Team",
            author_email="team@tripwire.dev",
            homepage="https://github.com/tripwire-plugins/vault",
            repository="https://github.com/tripwire-plugins/vault",
            license="MIT",
            versions={"0.1.0": version},
            latest_version="0.1.0",
        )

        return PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={"vault": entry},
        )

    def test_install_plugin_not_in_registry(self, mock_registry_client, tmp_path):
        """Test installing plugin not in registry."""
        installer = PluginInstaller(mock_registry_client)
        installer.PLUGINS_DIR = tmp_path

        # Mock registry without plugin
        mock_registry_client.fetch_registry.return_value = PluginRegistryIndex(
            version="1.0.0",
            updated_at="2025-01-01T00:00:00Z",
            plugins={},
        )

        with pytest.raises(RuntimeError, match="Plugin 'nonexistent' not found"):
            installer.install("nonexistent")

    def test_install_plugin_version_not_found(self, mock_registry_client, tmp_path):
        """Test installing non-existent version."""
        installer = PluginInstaller(mock_registry_client)
        installer.PLUGINS_DIR = tmp_path

        with pytest.raises(RuntimeError, match="Version '0.9.0' not found"):
            installer.install("vault", version="0.9.0")

    def test_install_plugin_already_installed_no_force(self, mock_registry_client, tmp_path):
        """Test installing already installed plugin without force."""
        installer = PluginInstaller(mock_registry_client)
        installer.PLUGINS_DIR = tmp_path

        # Create existing plugin directory
        plugin_dir = tmp_path / "vault"
        plugin_dir.mkdir()

        with pytest.raises(RuntimeError, match="already installed"):
            installer.install("vault")

    def test_list_installed_empty(self, tmp_path):
        """Test listing installed plugins when none installed."""
        installer = PluginInstaller()
        installer.PLUGINS_DIR = tmp_path

        installed = installer.list_installed()
        assert installed == []

    def test_list_installed_with_plugins(self, tmp_path):
        """Test listing installed plugins."""
        installer = PluginInstaller()
        installer.PLUGINS_DIR = tmp_path

        # Create plugin directories
        (tmp_path / "vault").mkdir()
        (tmp_path / "aws").mkdir()
        (tmp_path / ".hidden").mkdir()  # Should be ignored

        installed = installer.list_installed()
        assert len(installed) == 2
        assert "vault" in installed
        assert "aws" in installed
        assert ".hidden" not in installed

    def test_is_installed(self, tmp_path):
        """Test checking if plugin is installed."""
        installer = PluginInstaller()
        installer.PLUGINS_DIR = tmp_path

        # Create plugin directory
        (tmp_path / "vault").mkdir()

        assert installer.is_installed("vault")
        assert not installer.is_installed("aws")

    def test_uninstall_plugin(self, tmp_path):
        """Test uninstalling plugin."""
        installer = PluginInstaller()
        installer.PLUGINS_DIR = tmp_path

        # Create plugin directory
        plugin_dir = tmp_path / "vault"
        plugin_dir.mkdir()
        (plugin_dir / "file.py").write_text("# plugin code")

        assert installer.is_installed("vault")

        installer.uninstall("vault")

        assert not installer.is_installed("vault")
        assert not plugin_dir.exists()

    def test_uninstall_not_installed(self, tmp_path):
        """Test uninstalling non-existent plugin."""
        installer = PluginInstaller()
        installer.PLUGINS_DIR = tmp_path

        with pytest.raises(RuntimeError, match="not installed"):
            installer.uninstall("vault")
