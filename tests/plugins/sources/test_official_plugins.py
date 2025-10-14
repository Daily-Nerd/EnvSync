"""Comprehensive tests for official TripWire plugins.

Tests initialization, configuration validation, and metadata for all four official plugins:
- VaultEnvSource (HashiCorp Vault)
- AWSSecretsSource (AWS Secrets Manager)
- AzureKeyVaultSource (Azure Key Vault)
- RemoteConfigSource (HTTP/REST API)

Note: These tests focus on plugin initialization and validation without
requiring external dependencies (hvac, boto3, etc.) to be installed.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from tripwire.plugins.errors import PluginValidationError


class TestVaultEnvSource:
    """Tests for HashiCorp Vault plugin."""

    def test_initialization_with_params(self) -> None:
        """Test Vault plugin initialization with explicit parameters."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        vault = VaultEnvSource(
            url="https://vault.example.com",
            token="hvs.test123",
            mount_point="secret",
            path="myapp/config",
            kv_version=2,
        )

        assert vault.url == "https://vault.example.com"
        assert vault.token == "hvs.test123"
        assert vault.mount_point == "secret"
        assert vault.path == "myapp/config"
        assert vault.kv_version == 2
        assert vault.metadata.name == "vault"
        assert vault.metadata.version == "1.0.0"
        assert vault.metadata.author == "TripWire Team"
        assert "vault" in vault.metadata.tags

    def test_initialization_with_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Vault plugin initialization from environment variables."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        monkeypatch.setenv("VAULT_ADDR", "https://vault.test.com")
        monkeypatch.setenv("VAULT_TOKEN", "token456")
        monkeypatch.setenv("VAULT_PATH", "app/secrets")
        monkeypatch.setenv("VAULT_KV_VERSION", "1")

        vault = VaultEnvSource()

        assert vault.url == "https://vault.test.com"
        assert vault.token == "token456"
        assert vault.path == "app/secrets"
        assert vault.kv_version == 1

    def test_initialization_missing_required(self) -> None:
        """Test that missing required parameters raise PluginValidationError."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with pytest.raises(PluginValidationError) as exc:
            VaultEnvSource()

        assert "Vault URL is required" in str(exc.value)

    def test_initialization_invalid_kv_version(self) -> None:
        """Test that invalid KV version raises PluginValidationError."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        with pytest.raises(PluginValidationError) as exc:
            VaultEnvSource(
                url="https://vault.test.com",
                token="token",
                path="myapp",
                kv_version=3,  # Invalid
            )

        assert "Invalid KV version" in str(exc.value)

    def test_validate_config_valid(self) -> None:
        """Test config validation with valid configuration."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        vault = VaultEnvSource(url="https://vault.test.com", token="token", path="myapp")

        config = {
            "url": "https://vault.example.com",
            "token": "hvs.xxx",
            "path": "myapp/config",
            "kv_version": 2,
        }

        assert vault.validate_config(config) is True

    def test_validate_config_missing_required(self) -> None:
        """Test config validation with missing required fields."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        vault = VaultEnvSource(url="https://vault.test.com", token="token", path="myapp")

        config = {"url": "https://vault.example.com"}  # Missing token and path

        with pytest.raises(PluginValidationError) as exc:
            vault.validate_config(config)

        assert "Missing required field" in str(exc.value)


class TestAWSSecretsSource:
    """Tests for AWS Secrets Manager plugin."""

    def test_initialization_with_params(self) -> None:
        """Test AWS plugin initialization with explicit parameters."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        aws = AWSSecretsSource(
            secret_name="myapp/production",
            region_name="us-east-1",
            profile_name="default",
        )

        assert aws.secret_name == "myapp/production"
        assert aws.region_name == "us-east-1"
        assert aws.profile_name == "default"
        assert aws.metadata.name == "aws-secrets"
        assert "aws" in aws.metadata.tags

    def test_initialization_with_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test AWS plugin initialization from environment variables."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        monkeypatch.setenv("AWS_SECRET_NAME", "myapp/staging")
        monkeypatch.setenv("AWS_REGION", "eu-west-1")

        aws = AWSSecretsSource()

        assert aws.secret_name == "myapp/staging"
        assert aws.region_name == "eu-west-1"

    def test_initialization_missing_required(self) -> None:
        """Test that missing required parameters raise PluginValidationError."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        with pytest.raises(PluginValidationError) as exc:
            AWSSecretsSource()

        assert "Secret name is required" in str(exc.value)

    def test_sanitize_key(self) -> None:
        """Test secret name sanitization for env var names."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        aws = AWSSecretsSource(
            secret_name="myapp/production",
            region_name="us-east-1",
        )

        # Test various formats
        assert aws._sanitize_key("myapp/production/db-config") == "MYAPP_PRODUCTION_DB_CONFIG"
        assert aws._sanitize_key("api-key") == "API_KEY"

        # Test ARN format
        arn = "arn:aws:secretsmanager:us-east-1:123456:secret:myapp/config-AbCdEf"
        assert aws._sanitize_key(arn) == "MYAPP_CONFIG"

    def test_validate_config_valid(self) -> None:
        """Test config validation with valid configuration."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        aws = AWSSecretsSource(secret_name="myapp/config", region_name="us-east-1")

        config = {
            "secret_name": "myapp/production",
            "region_name": "us-east-1",
        }

        assert aws.validate_config(config) is True

    def test_validate_config_incomplete_credentials(self) -> None:
        """Test that incomplete explicit credentials fail validation."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        aws = AWSSecretsSource(secret_name="myapp/config", region_name="us-east-1")

        config = {
            "secret_name": "myapp/production",
            "region_name": "us-east-1",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            # Missing secret_access_key
        }

        with pytest.raises(PluginValidationError) as exc:
            aws.validate_config(config)

        assert "Both access_key_id and secret_access_key" in str(exc.value)


class TestAzureKeyVaultSource:
    """Tests for Azure Key Vault plugin."""

    def test_initialization_with_params(self) -> None:
        """Test Azure plugin initialization with explicit parameters."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        azure = AzureKeyVaultSource(
            vault_url="https://mykeyvault.vault.azure.net",
            secret_prefix="myapp-",
        )

        assert azure.vault_url == "https://mykeyvault.vault.azure.net"
        assert azure.secret_prefix == "myapp-"
        assert azure.metadata.name == "azure-keyvault"
        assert "azure" in azure.metadata.tags

    def test_initialization_with_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Azure plugin initialization from environment variables."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        monkeypatch.setenv("AZURE_KEYVAULT_URL", "https://testkeyvault.vault.azure.net")

        azure = AzureKeyVaultSource()

        assert azure.vault_url == "https://testkeyvault.vault.azure.net"

    def test_initialization_missing_required(self) -> None:
        """Test that missing Vault URL raises PluginValidationError."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        with pytest.raises(PluginValidationError) as exc:
            AzureKeyVaultSource()

        assert "Vault URL is required" in str(exc.value)

    def test_initialization_invalid_url_format(self) -> None:
        """Test that invalid Vault URL raises PluginValidationError."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        with pytest.raises(PluginValidationError) as exc:
            AzureKeyVaultSource(vault_url="http://invalid.com")

        assert "Invalid Azure Key Vault URL" in str(exc.value)

    def test_sanitize_key(self) -> None:
        """Test Azure secret name to env var conversion."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        assert azure._sanitize_key("database-url") == "DATABASE_URL"
        assert azure._sanitize_key("my-app-api-key") == "MY_APP_API_KEY"

    def test_sanitize_key_with_prefix(self) -> None:
        """Test secret name sanitization with prefix removal."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        azure = AzureKeyVaultSource(
            vault_url="https://mykeyvault.vault.azure.net",
            secret_prefix="myapp-",
        )

        assert azure._sanitize_key("myapp-database-url") == "DATABASE_URL"

    def test_validate_config_valid(self) -> None:
        """Test config validation with valid configuration."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        config = {"vault_url": "https://testkeyvault.vault.azure.net"}

        assert azure.validate_config(config) is True

    def test_validate_config_invalid_url(self) -> None:
        """Test config validation with invalid URL."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        config = {"vault_url": "http://invalid.com"}

        with pytest.raises(PluginValidationError) as exc:
            azure.validate_config(config)

        # Test updated error message after security fix
        assert "must use HTTPS" in str(exc.value) or "Invalid Azure Key Vault URL" in str(exc.value)


class TestRemoteConfigSource:
    """Tests for Remote HTTP Config plugin."""

    def test_initialization_with_params(self) -> None:
        """Test Remote Config plugin initialization with explicit parameters."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            format="json",
            headers={"Authorization": "Bearer token123"},
            timeout=60,
        )

        assert remote.url == "https://config.example.com/api/config"
        assert remote.format == "json"
        assert remote.timeout == 60
        assert remote.metadata.name == "remote-config"
        assert "config" in remote.metadata.tags

    def test_initialization_with_api_key(self) -> None:
        """Test initialization with API key."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            api_key="secret123",
            api_key_header="X-API-Key",
        )

        assert remote.headers["X-API-Key"] == "secret123"

    def test_initialization_with_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization from environment variables."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        monkeypatch.setenv("REMOTE_CONFIG_URL", "https://config.test.com/api")
        monkeypatch.setenv("REMOTE_CONFIG_FORMAT", "yaml")
        monkeypatch.setenv("REMOTE_CONFIG_API_KEY", "key123")

        remote = RemoteConfigSource()

        assert remote.url == "https://config.test.com/api"
        assert remote.format == "yaml"
        assert remote.api_key == "key123"

    def test_initialization_missing_required(self) -> None:
        """Test that missing URL raises PluginValidationError."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with pytest.raises(PluginValidationError) as exc:
            RemoteConfigSource()

        assert "URL is required" in str(exc.value)

    def test_initialization_invalid_format(self) -> None:
        """Test that invalid format raises PluginValidationError."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        with pytest.raises(PluginValidationError) as exc:
            RemoteConfigSource(
                url="https://config.example.com",
                format="xml",  # Invalid format
            )

        assert "Invalid format" in str(exc.value)

    def test_validate_config_valid(self) -> None:
        """Test config validation with valid configuration."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(url="https://config.example.com/api/config")

        config = {
            "url": "https://config.example.com/api/config",
            "format": "json",
            "timeout": 30,
        }

        assert remote.validate_config(config) is True

    def test_validate_config_invalid_url_protocol(self) -> None:
        """Test config validation with invalid URL protocol."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(url="https://config.example.com/api/config")

        config = {"url": "ftp://invalid.com"}  # Invalid protocol

        with pytest.raises(PluginValidationError) as exc:
            remote.validate_config(config)

        # Updated for new security validation - invalid schemes now show "Invalid URL scheme"
        assert "Invalid URL scheme" in str(exc.value) or "must start with 'http://'" in str(exc.value)

    def test_validate_config_invalid_format(self) -> None:
        """Test config validation with invalid format."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        remote = RemoteConfigSource(url="https://config.example.com/api/config")

        config = {
            "url": "https://config.example.com/api/config",
            "format": "xml",  # Invalid
        }

        with pytest.raises(PluginValidationError) as exc:
            remote.validate_config(config)

        assert "Invalid format" in str(exc.value)


# Integration tests for all plugins
class TestPluginIntegration:
    """Integration tests for plugin system."""

    def test_all_plugins_have_metadata(self) -> None:
        """Test that all official plugins have valid metadata."""
        from tripwire.plugins.sources import (
            AWSSecretsSource,
            AzureKeyVaultSource,
            RemoteConfigSource,
            VaultEnvSource,
        )

        plugins = [
            (VaultEnvSource, {"url": "https://vault.test", "token": "t", "path": "p"}),
            (AWSSecretsSource, {"secret_name": "s", "region_name": "us-east-1"}),
            (AzureKeyVaultSource, {"vault_url": "https://kv.vault.azure.net"}),
            (RemoteConfigSource, {"url": "https://config.test"}),
        ]

        for plugin_class, init_args in plugins:
            plugin = plugin_class(**init_args)
            metadata = plugin.metadata

            assert metadata.name
            assert metadata.version
            assert metadata.author == "TripWire Team"
            assert metadata.description
            assert metadata.min_tripwire_version == "0.10.0"
            assert len(metadata.tags) > 0

    def test_all_plugins_implement_protocol(self) -> None:
        """Test that all plugins implement the EnvSourcePlugin protocol."""
        from tripwire.plugins.sources import (
            AWSSecretsSource,
            AzureKeyVaultSource,
            RemoteConfigSource,
            VaultEnvSource,
        )

        plugins = [
            VaultEnvSource(url="https://vault.test", token="t", path="p"),
            AWSSecretsSource(secret_name="s", region_name="us-east-1"),
            AzureKeyVaultSource(vault_url="https://kv.vault.azure.net"),
            RemoteConfigSource(url="https://config.test"),
        ]

        for plugin in plugins:
            # Check for required methods/properties
            assert hasattr(plugin, "metadata")
            assert hasattr(plugin, "load")
            assert hasattr(plugin, "validate_config")
            assert callable(plugin.load)
            assert callable(plugin.validate_config)

    def test_all_plugins_have_consistent_metadata(self) -> None:
        """Test that all plugins have consistent metadata structure."""
        from tripwire.plugins.sources import (
            AWSSecretsSource,
            AzureKeyVaultSource,
            RemoteConfigSource,
            VaultEnvSource,
        )

        plugins = [
            VaultEnvSource(url="https://vault.test", token="t", path="p"),
            AWSSecretsSource(secret_name="s", region_name="us-east-1"),
            AzureKeyVaultSource(vault_url="https://kv.vault.azure.net"),
            RemoteConfigSource(url="https://config.test"),
        ]

        for plugin in plugins:
            metadata = plugin.metadata
            # All plugins should have:
            assert metadata.name
            assert metadata.version
            assert metadata.author
            assert metadata.description
            assert metadata.min_tripwire_version
            assert isinstance(metadata.tags, list)
            # Version should follow semver
            assert len(metadata.version.split(".")) >= 2


# ============================================================================
# LOAD() METHOD TESTS - Mock-based integration tests for all plugins
# ============================================================================


class TestVaultEnvSourceLoad:
    """Tests for VaultEnvSource.load() method with mocked hvac library."""

    def test_load_kv_v2_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load from Vault KV v2 engine."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        # Mock hvac client
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "DATABASE_URL": "postgresql://localhost/db",
                    "API_KEY": "secret123",
                    "PORT": 8080,
                    "DEBUG": True,
                }
            }
        }

        # Mock hvac module
        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="hvs.test",
            path="myapp/config",
            kv_version=2,
        )

        result = vault.load()

        assert result == {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "secret123",
            "PORT": "8080",
            "DEBUG": "True",
        }
        mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with(
            path="myapp/config",
            mount_point="secret",
        )

    def test_load_kv_v1_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load from Vault KV v1 engine."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v1.read_secret.return_value = {
            "data": {
                "API_KEY": "key123",
                "SECRET_TOKEN": "token456",
            }
        }

        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="hvs.test",
            path="myapp/secrets",
            kv_version=1,
        )

        result = vault.load()

        assert result == {
            "API_KEY": "key123",
            "SECRET_TOKEN": "token456",
        }
        mock_client.secrets.kv.v1.read_secret.assert_called_once_with(
            path="myapp/secrets",
            mount_point="secret",
        )

    def test_load_authentication_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to authentication error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.vault import VaultEnvSource

        mock_client = Mock()
        mock_client.is_authenticated.return_value = False

        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="invalid_token",
            path="myapp/config",
        )

        with pytest.raises(PluginAPIError) as exc:
            vault.load()

        assert "authentication failed" in str(exc.value).lower()

    def test_load_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to connection error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.vault import VaultEnvSource

        mock_client = Mock()
        mock_client.is_authenticated.side_effect = ConnectionError("Connection refused")

        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="hvs.test",
            path="myapp/config",
        )

        with pytest.raises(PluginAPIError) as exc:
            vault.load()

        assert "Failed to load secrets" in str(exc.value)

    def test_load_path_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure when secret path doesn't exist."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.vault import VaultEnvSource

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("path not found")

        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="hvs.test",
            path="nonexistent/path",
        )

        with pytest.raises(PluginAPIError) as exc:
            vault.load()

        assert "Failed to load secrets" in str(exc.value)

    def test_load_skips_complex_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that load() skips complex types (lists, dicts)."""
        from tripwire.plugins.sources.vault import VaultEnvSource

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "SIMPLE_KEY": "value",
                    "NESTED_DICT": {"key": "value"},  # Should be skipped
                    "LIST_VALUE": [1, 2, 3],  # Should be skipped
                }
            }
        }

        mock_hvac = Mock()
        mock_hvac.Client.return_value = mock_client
        monkeypatch.setitem(__import__("sys").modules, "hvac", mock_hvac)

        vault = VaultEnvSource(
            url="https://vault.test.com",
            token="hvs.test",
            path="myapp/config",
        )

        result = vault.load()

        # Only simple key should be present
        assert result == {"SIMPLE_KEY": "value"}


class TestAWSSecretsSourceLoad:
    """Tests for AWSSecretsSource.load() method with mocked boto3 library."""

    def test_load_json_secret_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load of JSON secret from AWS Secrets Manager."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {
            "SecretString": '{"DATABASE_URL": "postgresql://db", "API_KEY": "key123"}'
        }

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="myapp/production",
            region_name="us-east-1",
        )

        result = aws.load()

        assert result == {
            "DATABASE_URL": "postgresql://db",
            "API_KEY": "key123",
        }
        mock_client.get_secret_value.assert_called_once_with(SecretId="myapp/production")

    def test_load_string_secret_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load of plain string secret."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": "plain_secret_value"}

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="myapp/api-key",
            region_name="us-east-1",
        )

        result = aws.load()

        # Plain string becomes env var with sanitized name
        assert result == {"MYAPP_API_KEY": "plain_secret_value"}

    def test_load_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to AWS connection error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        mock_client.get_secret_value.side_effect = ConnectionError("Network error")

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="myapp/config",
            region_name="us-east-1",
        )

        with pytest.raises(PluginAPIError) as exc:
            aws.load()

        assert "Failed to load secret" in str(exc.value)

    def test_load_secret_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure when secret doesn't exist."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        mock_client.get_secret_value.side_effect = Exception("ResourceNotFoundException: Secret not found")

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="nonexistent/secret",
            region_name="us-east-1",
        )

        with pytest.raises(PluginAPIError) as exc:
            aws.load()

        assert "Failed to load secret" in str(exc.value)

    def test_load_nested_json_flattened(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that nested JSON structures are flattened correctly."""
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        mock_client.get_secret_value.return_value = {
            "SecretString": '{"key1": "value1", "key2": 123, "nested": {"inner": "skip"}}'
        }

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="myapp/config",
            region_name="us-east-1",
        )

        result = aws.load()

        # Nested dict should be skipped, only simple values extracted
        assert "key1" in result
        assert "key2" in result
        assert "nested" not in result

    def test_load_binary_secret_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure when secret contains binary data."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.aws_secrets import AWSSecretsSource

        mock_client = Mock()
        # Binary secret has no SecretString
        mock_client.get_secret_value.return_value = {"SecretBinary": b"binary_data"}

        mock_session = Mock()
        mock_session.client.return_value = mock_client

        mock_boto3 = Mock()
        mock_boto3.Session.return_value = mock_session
        monkeypatch.setitem(__import__("sys").modules, "boto3", mock_boto3)

        aws = AWSSecretsSource(
            secret_name="myapp/binary-secret",
            region_name="us-east-1",
        )

        with pytest.raises(PluginAPIError) as exc:
            aws.load()

        assert "binary data" in str(exc.value).lower()


class TestAzureKeyVaultSourceLoad:
    """Tests for AzureKeyVaultSource.load() method with mocked Azure SDK."""

    def test_load_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load from Azure Key Vault."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        # Mock secret properties
        mock_secret1 = Mock()
        mock_secret1.name = "database-url"
        mock_secret2 = Mock()
        mock_secret2.name = "api-key"

        # Mock secret values
        mock_value1 = Mock()
        mock_value1.value = "postgresql://db"
        mock_value2 = Mock()
        mock_value2.value = "secret123"

        mock_client = Mock()
        mock_client.list_properties_of_secrets.return_value = [mock_secret1, mock_secret2]
        mock_client.get_secret.side_effect = [mock_value1, mock_value2]

        # Mock Azure SDK
        mock_azure = Mock()
        mock_azure.SecretClient.return_value = mock_client
        mock_identity = Mock()
        mock_identity.DefaultAzureCredential.return_value = Mock()

        monkeypatch.setitem(__import__("sys").modules, "azure.keyvault.secrets", mock_azure)
        monkeypatch.setitem(__import__("sys").modules, "azure.identity", mock_identity)

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        result = azure.load()

        assert result == {
            "DATABASE_URL": "postgresql://db",
            "API_KEY": "secret123",
        }

    def test_load_with_prefix_filter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load with secret prefix filtering."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        mock_secret1 = Mock()
        mock_secret1.name = "myapp-database-url"
        mock_secret2 = Mock()
        mock_secret2.name = "other-secret"  # Should be filtered out

        mock_value1 = Mock()
        mock_value1.value = "postgresql://db"

        mock_client = Mock()
        mock_client.list_properties_of_secrets.return_value = [mock_secret1, mock_secret2]
        mock_client.get_secret.return_value = mock_value1

        mock_azure = Mock()
        mock_azure.SecretClient.return_value = mock_client
        mock_identity = Mock()
        mock_identity.DefaultAzureCredential.return_value = Mock()

        monkeypatch.setitem(__import__("sys").modules, "azure.keyvault.secrets", mock_azure)
        monkeypatch.setitem(__import__("sys").modules, "azure.identity", mock_identity)

        azure = AzureKeyVaultSource(
            vault_url="https://mykeyvault.vault.azure.net",
            secret_prefix="myapp-",
        )

        result = azure.load()

        # Only myapp- prefixed secret should be loaded, with prefix removed
        assert "DATABASE_URL" in result
        assert len(result) == 1

    def test_load_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to Azure connection error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        mock_client = Mock()
        mock_client.list_properties_of_secrets.side_effect = ConnectionError("Network error")

        mock_azure = Mock()
        mock_azure.SecretClient.return_value = mock_client
        mock_identity = Mock()
        mock_identity.DefaultAzureCredential.return_value = Mock()

        monkeypatch.setitem(__import__("sys").modules, "azure.keyvault.secrets", mock_azure)
        monkeypatch.setitem(__import__("sys").modules, "azure.identity", mock_identity)

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        with pytest.raises(PluginAPIError) as exc:
            azure.load()

        assert "Failed to load secrets" in str(exc.value)

    def test_load_authentication_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to authentication error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        mock_client = Mock()
        mock_client.list_properties_of_secrets.side_effect = Exception("AuthenticationFailed")

        mock_azure = Mock()
        mock_azure.SecretClient.return_value = mock_client
        mock_identity = Mock()
        mock_identity.DefaultAzureCredential.return_value = Mock()

        monkeypatch.setitem(__import__("sys").modules, "azure.keyvault.secrets", mock_azure)
        monkeypatch.setitem(__import__("sys").modules, "azure.identity", mock_identity)

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        with pytest.raises(PluginAPIError) as exc:
            azure.load()

        assert "Failed to load secrets" in str(exc.value)

    def test_load_partial_failure_continues(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that load continues even if some secrets fail."""
        from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource

        mock_secret1 = Mock()
        mock_secret1.name = "working-secret"
        mock_secret2 = Mock()
        mock_secret2.name = "failing-secret"

        mock_value1 = Mock()
        mock_value1.value = "value123"

        mock_client = Mock()
        mock_client.list_properties_of_secrets.return_value = [mock_secret1, mock_secret2]
        # First get_secret succeeds, second fails
        mock_client.get_secret.side_effect = [mock_value1, Exception("Secret access denied")]

        mock_azure = Mock()
        mock_azure.SecretClient.return_value = mock_client
        mock_identity = Mock()
        mock_identity.DefaultAzureCredential.return_value = Mock()

        monkeypatch.setitem(__import__("sys").modules, "azure.keyvault.secrets", mock_azure)
        monkeypatch.setitem(__import__("sys").modules, "azure.identity", mock_identity)

        azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")

        result = azure.load()

        # Should still have the working secret
        assert "WORKING_SECRET" in result


class TestRemoteConfigSourceLoad:
    """Tests for RemoteConfigSource.load() method with mocked HTTP requests."""

    def test_load_json_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load of JSON configuration."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"DATABASE_URL": "postgresql://db", "API_KEY": "key123"}'
        mock_response.json.return_value = {"DATABASE_URL": "postgresql://db", "API_KEY": "key123"}
        mock_response.raise_for_status = Mock()

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            format="json",
        )

        result = remote.load()

        assert result == {
            "DATABASE_URL": "postgresql://db",
            "API_KEY": "key123",
        }
        mock_requests.get.assert_called_once()

    def test_load_yaml_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful load of YAML configuration."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        yaml_content = """
database_url: postgresql://db
api_key: key123
port: 8080
"""

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = yaml_content
        mock_response.raise_for_status = Mock()

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        mock_yaml = Mock()
        mock_yaml.safe_load.return_value = {
            "database_url": "postgresql://db",
            "api_key": "key123",
            "port": 8080,
        }

        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)
        monkeypatch.setitem(__import__("sys").modules, "yaml", mock_yaml)

        remote = RemoteConfigSource(
            url="https://config.example.com/config.yaml",
            format="yaml",
        )

        result = remote.load()

        assert "database_url" in result
        assert "api_key" in result

    def test_load_connection_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to connection error."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_requests = Mock()
        mock_requests.get.side_effect = ConnectionError("Connection refused")
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
        )

        with pytest.raises(PluginAPIError) as exc:
            remote.load()

        assert "Failed to load configuration" in str(exc.value)

    def test_load_authentication_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure due to authentication error (401/403)."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            api_key="invalid_key",
        )

        with pytest.raises(PluginAPIError) as exc:
            remote.load()

        assert "Failed to load configuration" in str(exc.value)

    def test_load_invalid_json_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load failure when JSON is malformed."""
        from tripwire.plugins.errors import PluginAPIError
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "{invalid json}"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            format="json",
        )

        with pytest.raises(PluginAPIError) as exc:
            remote.load()

        assert "Failed to parse" in str(exc.value)

    def test_load_with_custom_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load with custom HTTP headers."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            headers={"Authorization": "Bearer token123", "X-Custom": "header"},
        )

        result = remote.load()

        # Verify headers were passed
        call_kwargs = mock_requests.get.call_args[1]
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]

    def test_load_with_api_key_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test load with API key authentication."""
        from tripwire.plugins.sources.remote_config import RemoteConfigSource

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status = Mock()

        mock_requests = Mock()
        mock_requests.get.return_value = mock_response
        monkeypatch.setitem(__import__("sys").modules, "requests", mock_requests)

        remote = RemoteConfigSource(
            url="https://config.example.com/api/config",
            api_key="secret123",
            api_key_header="X-API-Key",
        )

        result = remote.load()

        # Verify API key was added to headers
        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["headers"]["X-API-Key"] == "secret123"
