"""Comprehensive tests for TripWire plugin CLI commands.

Tests all 5 plugin CLI commands with focus on:
- Success paths (happy paths)
- Error handling (failure paths)
- Edge cases (boundary conditions)
- User interaction (confirmation prompts)
- Output verification (messages, exit codes)

Coverage target: 90%+ for all plugin CLI commands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from tripwire.plugins.registry import (
    PluginInstaller,
    PluginRegistryClient,
    PluginRegistryEntry,
    PluginRegistryIndex,
    PluginVersionInfo,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create CLI runner for testing Click commands."""
    return CliRunner()


@pytest.fixture
def mock_registry() -> PluginRegistryIndex:
    """Create mock registry with sample plugins."""
    vault_version = PluginVersionInfo(
        version="0.2.0",
        release_date="2024-01-15",
        min_tripwire_version="0.10.0",
        download_url="https://github.com/test/vault/releases/0.2.0/vault.tar.gz",
        checksum="sha256:abc123",
        downloads=100,
    )

    aws_version = PluginVersionInfo(
        version="0.3.0",
        release_date="2024-02-01",
        min_tripwire_version="0.10.0",
        download_url="https://github.com/test/aws/releases/0.3.0/aws.tar.gz",
        checksum="sha256:def456",
        downloads=200,
    )

    vault_entry = PluginRegistryEntry(
        name="vault",
        display_name="HashiCorp Vault",
        description="HashiCorp Vault KV secrets integration",
        author="TripWire Team",
        author_email="team@tripwire.com",
        homepage="https://github.com/test/vault",
        repository="https://github.com/test/vault",
        license="MIT",
        tags=["secrets", "vault", "hashicorp"],
        versions={"0.2.0": vault_version},
        latest_version="0.2.0",
        total_downloads=100,
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-15T00:00:00Z",
    )

    aws_entry = PluginRegistryEntry(
        name="aws-secrets",
        display_name="AWS Secrets Manager",
        description="AWS Secrets Manager integration",
        author="TripWire Team",
        author_email="team@tripwire.com",
        homepage="https://github.com/test/aws",
        repository="https://github.com/test/aws",
        license="MIT",
        tags=["secrets", "aws", "cloud"],
        versions={"0.3.0": aws_version},
        latest_version="0.3.0",
        total_downloads=200,
        created_at="2024-02-01T00:00:00Z",
        updated_at="2024-02-01T00:00:00Z",
    )

    return PluginRegistryIndex(
        version="1.0.0",
        updated_at="2024-02-01T00:00:00Z",
        plugins={
            "vault": vault_entry,
            "aws-secrets": aws_entry,
        },
    )


@pytest.fixture
def mock_registry_client(mock_registry: PluginRegistryIndex) -> Mock:
    """Create mock registry client."""
    client = Mock(spec=PluginRegistryClient)
    client.fetch_registry.return_value = mock_registry
    return client


@pytest.fixture
def mock_installer() -> Mock:
    """Create mock plugin installer."""
    installer = Mock(spec=PluginInstaller)
    installer.PLUGINS_DIR = Path.home() / ".tripwire" / "plugins"
    installer.list_installed.return_value = []
    installer.is_installed.return_value = False
    return installer


# ============================================================================
# PLUGIN INSTALL COMMAND TESTS
# ============================================================================


class TestPluginInstallCommand:
    """Tests for 'tripwire plugin install' command."""

    def test_install_success(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
        mock_registry: PluginRegistryIndex,
    ) -> None:
        """Test successful plugin installation."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault"])

        assert result.exit_code == 0
        assert "Installing HashiCorp Vault" in result.output
        assert "Plugin 'vault' installed successfully" in result.output
        assert "Version: 0.2.0" in result.output
        mock_installer.install.assert_called_once_with(
            plugin_id="vault",
            version="0.2.0",
            force=False,
        )

    def test_install_with_specific_version(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test installing a specific plugin version."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault", "--version", "0.2.0"])

        assert result.exit_code == 0
        assert "Version: 0.2.0" in result.output
        mock_installer.install.assert_called_once_with(
            plugin_id="vault",
            version="0.2.0",
            force=False,
        )

    def test_install_with_force_flag(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test force reinstall of plugin."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault", "--force"])

        assert result.exit_code == 0
        mock_installer.install.assert_called_once_with(
            plugin_id="vault",
            version="0.2.0",
            force=True,
        )

    def test_install_plugin_not_found(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test installing non-existent plugin."""
        from tripwire.cli.commands.plugin.install import install

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["nonexistent-plugin"])

        assert result.exit_code == 1
        assert "Plugin 'nonexistent-plugin' not found in registry" in result.output
        assert "Use" in result.output and "tripwire plugin search" in result.output
        mock_installer.install.assert_not_called()

    def test_install_version_not_found(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test installing non-existent version."""
        from tripwire.cli.commands.plugin.install import install

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault", "--version", "99.99.99"])

        assert result.exit_code == 1
        assert "Version '99.99.99' not found" in result.output
        assert "Available versions:" in result.output
        mock_installer.install.assert_not_called()

    def test_install_already_installed_error(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test error when plugin is already installed."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.side_effect = RuntimeError(
            "Plugin 'vault' is already installed. Use --force to reinstall."
        )

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault"])

        assert result.exit_code == 1
        assert "already installed" in result.output
        assert "Use" in result.output and "--force" in result.output

    def test_install_network_error(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test installation failure due to network error."""
        from tripwire.cli.commands.plugin.install import install

        mock_client = Mock(spec=PluginRegistryClient)
        mock_client.fetch_registry.side_effect = RuntimeError("Failed to fetch plugin registry: Network error")

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault"])

        assert result.exit_code == 1
        assert "Installation failed" in result.output or "Failed to fetch plugin registry" in result.output

    def test_install_with_no_cache_flag(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test installation without cache."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault", "--no-cache"])

        assert result.exit_code == 0
        mock_registry_client.fetch_registry.assert_called_once_with(use_cache=False)

    def test_install_download_failure(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
        mock_installer: Mock,
    ) -> None:
        """Test installation failure during download."""
        from tripwire.cli.commands.plugin.install import install

        mock_installer.install.side_effect = RuntimeError("Failed to download plugin: Connection timeout")

        with patch("tripwire.cli.commands.plugin.install.PluginRegistryClient", return_value=mock_registry_client):
            with patch("tripwire.cli.commands.plugin.install.PluginInstaller", return_value=mock_installer):
                result = cli_runner.invoke(install, ["vault"])

        assert result.exit_code == 1
        assert "Failed to download plugin" in result.output or "Installation failed" in result.output


# ============================================================================
# PLUGIN SEARCH COMMAND TESTS
# ============================================================================


class TestPluginSearchCommand:
    """Tests for 'tripwire plugin search' command."""

    def test_search_with_results(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test searching plugins with matching results."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, ["vault"])

        assert result.exit_code == 0
        assert "Plugin Search Results" in result.output
        assert "vault" in result.output.lower()
        assert "HashiCorp Vault" in result.output
        assert "To install:" in result.output

    def test_search_all_plugins(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test listing all plugins with empty query."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, [])

        assert result.exit_code == 0
        assert "vault" in result.output.lower()
        # aws-secrets may be truncated in table display
        assert "aws-secrets" in result.output.lower() or "aws-secre" in result.output.lower()

    def test_search_no_results(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test search with no matching results."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, ["nonexistent"])

        assert result.exit_code == 0
        assert "No plugins found matching 'nonexistent'" in result.output
        assert "Try a different search term" in result.output

    def test_search_with_limit(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test search with result limit."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, ["--limit", "1"])

        assert result.exit_code == 0
        # Should only show one plugin in results

    def test_search_network_error(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test search failure due to network error."""
        from tripwire.cli.commands.plugin.search import search

        mock_client = Mock(spec=PluginRegistryClient)
        mock_client.fetch_registry.side_effect = RuntimeError("Network error fetching registry")

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_client):
            result = cli_runner.invoke(search, ["vault"])

        assert result.exit_code == 1
        assert "Search failed" in result.output
        assert "Check your internet connection" in result.output

    def test_search_with_no_cache(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test search without using cache."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, ["vault", "--no-cache"])

        assert result.exit_code == 0
        mock_registry_client.fetch_registry.assert_called_once_with(use_cache=False)


# ============================================================================
# PLUGIN LIST COMMAND TESTS
# ============================================================================


class TestPluginListCommand:
    """Tests for 'tripwire plugin list' command."""

    def test_list_empty(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test listing plugins when none are installed."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer.list_installed.return_value = []

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(list_plugins, [])

        assert result.exit_code == 0
        assert "No plugins installed" in result.output
        assert "tripwire plugin install" in result.output
        assert "tripwire plugin search" in result.output

    def test_list_with_plugins(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test listing installed plugins (simple mode)."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer.list_installed.return_value = ["vault", "aws-secrets"]

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(list_plugins, [])

        assert result.exit_code == 0
        assert "Installed Plugins:" in result.output
        assert "vault" in result.output
        assert "aws-secrets" in result.output
        assert "2 plugins installed" in result.output

    def test_list_with_details(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test listing plugins with detailed information."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer.list_installed.return_value = ["vault", "aws-secrets"]

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.ls.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(list_plugins, ["--details"])

        assert result.exit_code == 0
        assert "Installed Plugins" in result.output
        assert "vault" in result.output
        assert "HashiCorp Vault" in result.output
        assert "TripWire Team" in result.output
        assert "MIT" in result.output

    def test_list_with_details_custom_plugin(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test listing with details including custom plugin not in registry."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer.list_installed.return_value = ["vault", "custom-plugin"]

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.ls.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(list_plugins, ["--details"])

        assert result.exit_code == 0
        assert "vault" in result.output
        assert "custom-plugin" in result.output
        assert "unknown" in result.output  # Custom plugins show "unknown" for missing info

    def test_list_error_handling(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """Test error handling in list command."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer = Mock(spec=PluginInstaller)
        mock_installer.list_installed.side_effect = RuntimeError("Failed to read plugins directory")

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(list_plugins, [])

        assert result.exit_code == 1
        assert "Failed to list plugins" in result.output


# ============================================================================
# PLUGIN UPDATE COMMAND TESTS
# ============================================================================


class TestPluginUpdateCommand:
    """Tests for 'tripwire plugin update' command."""

    def test_update_success(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test successful plugin update."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True
        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault"])

        assert result.exit_code == 0
        assert "Updating HashiCorp Vault" in result.output
        assert "updated successfully" in result.output
        assert "Target version: 0.2.0" in result.output
        mock_installer.install.assert_called_once_with(
            plugin_id="vault",
            version="0.2.0",
            force=True,  # Update always uses force
        )

    def test_update_to_specific_version(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test updating to specific version."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True
        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault", "--version", "0.2.0"])

        assert result.exit_code == 0
        mock_installer.install.assert_called_once_with(
            plugin_id="vault",
            version="0.2.0",
            force=True,
        )

    def test_update_not_installed(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test update when plugin is not installed."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = False

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault"])

        assert result.exit_code == 1
        assert "Plugin 'vault' is not installed" in result.output
        assert "Install it first" in result.output
        mock_installer.install.assert_not_called()

    def test_update_not_in_registry(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test update when plugin is not in registry."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["custom-plugin"])

        assert result.exit_code == 1
        assert "Plugin 'custom-plugin' not found in registry" in result.output
        assert "custom plugin" in result.output.lower()

    def test_update_version_not_found(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test update to non-existent version."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault", "--version", "99.99.99"])

        assert result.exit_code == 1
        assert "Version '99.99.99' not found" in result.output
        assert "Available versions:" in result.output

    def test_update_failure(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test update failure during installation."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True
        mock_installer.install.side_effect = RuntimeError("Download failed")

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault"])

        assert result.exit_code == 1
        assert "Update failed" in result.output

    def test_update_with_no_cache(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
        mock_registry_client: Mock,
    ) -> None:
        """Test update without using cache."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.return_value = True
        mock_installer.install.return_value = Path.home() / ".tripwire" / "plugins" / "vault"

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.update.PluginRegistryClient", return_value=mock_registry_client):
                result = cli_runner.invoke(update, ["vault", "--no-cache"])

        assert result.exit_code == 0
        mock_registry_client.fetch_registry.assert_called_once_with(use_cache=False)


# ============================================================================
# PLUGIN REMOVE COMMAND TESTS
# ============================================================================


class TestPluginRemoveCommand:
    """Tests for 'tripwire plugin remove' command."""

    def test_remove_success_with_yes_flag(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test successful plugin removal with --yes flag."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(remove, ["vault", "--yes"])

        assert result.exit_code == 0
        assert "Plugin 'vault' removed successfully" in result.output
        mock_installer.uninstall.assert_called_once_with("vault")

    def test_remove_success_with_confirmation(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test successful plugin removal with user confirmation."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            # Simulate user confirming with 'y'
            result = cli_runner.invoke(remove, ["vault"], input="y\n")

        assert result.exit_code == 0
        assert "removed successfully" in result.output
        mock_installer.uninstall.assert_called_once_with("vault")

    def test_remove_cancelled_by_user(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test plugin removal cancelled by user."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            # Simulate user declining with 'n'
            result = cli_runner.invoke(remove, ["vault"], input="n\n")

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_installer.uninstall.assert_not_called()

    def test_remove_not_installed(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test removing plugin that is not installed."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = False

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(remove, ["vault", "--yes"])

        assert result.exit_code == 1
        assert "Plugin 'vault' is not installed" in result.output
        assert "tripwire plugin list" in result.output
        mock_installer.uninstall.assert_not_called()

    def test_remove_failure(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test removal failure during uninstall."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = True
        mock_installer.uninstall.side_effect = RuntimeError("Permission denied")

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(remove, ["vault", "--yes"])

        assert result.exit_code == 1
        assert "Failed to remove plugin" in result.output

    def test_remove_shows_warning_message(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test that removal shows warning message."""
        from tripwire.cli.commands.plugin.remove import remove

        mock_installer.is_installed.return_value = True

        with patch("tripwire.cli.commands.plugin.remove.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(remove, ["vault"], input="n\n")

        # Warning should be shown
        assert "about to remove" in result.output.lower()
        assert "This action cannot be undone" in result.output


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestPluginCommandsEdgeCases:
    """Edge case and error handling tests for plugin commands."""

    def test_install_empty_plugin_id(self, cli_runner: CliRunner) -> None:
        """Test install with missing plugin ID."""
        from tripwire.cli.commands.plugin.install import install

        result = cli_runner.invoke(install, [])

        assert result.exit_code != 0

    def test_search_with_special_characters(
        self,
        cli_runner: CliRunner,
        mock_registry_client: Mock,
    ) -> None:
        """Test search with special characters in query."""
        from tripwire.cli.commands.plugin.search import search

        with patch("tripwire.cli.commands.plugin.search.PluginRegistryClient", return_value=mock_registry_client):
            result = cli_runner.invoke(search, ["@#$%"])

        assert result.exit_code == 0  # Should handle gracefully

    def test_update_unexpected_error(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test update with unexpected error."""
        from tripwire.cli.commands.plugin.update import update

        mock_installer.is_installed.side_effect = Exception("Unexpected error")

        with patch("tripwire.cli.commands.plugin.update.PluginInstaller", return_value=mock_installer):
            result = cli_runner.invoke(update, ["vault"])

        assert result.exit_code == 1

    def test_list_registry_fetch_failure_in_details(
        self,
        cli_runner: CliRunner,
        mock_installer: Mock,
    ) -> None:
        """Test list --details when registry fetch fails."""
        from tripwire.cli.commands.plugin.ls import list_plugins

        mock_installer.list_installed.return_value = ["vault"]
        mock_client = Mock(spec=PluginRegistryClient)
        mock_client.fetch_registry.side_effect = RuntimeError("Network error")

        with patch("tripwire.cli.commands.plugin.ls.PluginInstaller", return_value=mock_installer):
            with patch("tripwire.cli.commands.plugin.ls.PluginRegistryClient", return_value=mock_client):
                result = cli_runner.invoke(list_plugins, ["--details"])

        # Should fail gracefully
        assert result.exit_code != 0
