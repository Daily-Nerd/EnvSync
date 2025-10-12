"""Azure Key Vault plugin for TripWire.

This plugin enables reading secrets from Azure Key Vault with support for
multiple authentication methods via Azure Identity.

Dependencies:
    azure-keyvault-secrets>=4.8.0
    azure-identity>=1.15.0

Installation:
    pip install azure-keyvault-secrets azure-identity

Usage:
    >>> from tripwire.plugins.sources import AzureKeyVaultSource
    >>> from tripwire import TripWire
    >>>
    >>> azure = AzureKeyVaultSource(
    ...     vault_url="https://mykeyvault.vault.azure.net",
    ...     # Authentication handled automatically via DefaultAzureCredential
    ... )
    >>> env = TripWire(sources=[azure])

Authentication (via DefaultAzureCredential, in order):
    1. AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET (service principal)
    2. Managed Identity (when running on Azure VMs, App Service, Functions, etc.)
    3. Azure CLI credentials (az login)
    4. Azure PowerShell credentials
    5. Visual Studio Code credentials

Environment Variables:
    AZURE_KEYVAULT_URL: Key Vault URL
    AZURE_CLIENT_ID: Service principal client ID
    AZURE_TENANT_ID: Azure AD tenant ID
    AZURE_CLIENT_SECRET: Service principal secret
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

from tripwire.plugins.base import PluginInterface, PluginMetadata
from tripwire.plugins.errors import PluginAPIError, PluginValidationError


class AzureKeyVaultSource(PluginInterface):
    """Azure Key Vault secrets plugin.

    Reads environment variables from Azure Key Vault. Uses DefaultAzureCredential
    for authentication, which supports multiple authentication flows.

    Attributes:
        vault_url: Key Vault URL (e.g., "https://mykeyvault.vault.azure.net")
        secret_prefix: Optional prefix to filter secrets (e.g., "myapp-")
        credential: Optional custom credential object (defaults to DefaultAzureCredential)

    Example:
        >>> azure = AzureKeyVaultSource(
        ...     vault_url="https://mykeyvault.vault.azure.net"
        ... )
        >>> secrets = azure.load()
        >>> print(secrets["DATABASE-URL"])  # Note: Azure uses hyphens, not underscores
    """

    def __init__(
        self,
        vault_url: str | None = None,
        secret_prefix: str | None = None,
        credential: Any | None = None,
    ) -> None:
        """Initialize Azure Key Vault plugin.

        Args:
            vault_url: Key Vault URL (or set AZURE_KEYVAULT_URL env var)
            secret_prefix: Optional prefix to filter secrets (e.g., "myapp-")
            credential: Custom Azure credential (defaults to DefaultAzureCredential)

        Raises:
            PluginValidationError: If required parameters are missing
        """
        metadata = PluginMetadata(
            name="azure-keyvault",
            version="1.0.0",
            author="TripWire Team",
            description="Azure Key Vault secrets integration",
            homepage="https://github.com/Daily-Nerd/TripWire",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["secrets", "azure", "cloud", "microsoft"],
        )
        super().__init__(metadata)

        # Allow environment variables as fallback
        self.vault_url = vault_url or os.getenv("AZURE_KEYVAULT_URL")
        self.secret_prefix = secret_prefix
        self._credential = credential

        # Validate required parameters
        errors: list[str] = []
        if not self.vault_url:
            errors.append("Vault URL is required (vault_url parameter or AZURE_KEYVAULT_URL env var)")

        # Validate URL format with proper domain verification
        if self.vault_url:
            try:
                parsed = urlparse(self.vault_url)
                if parsed.scheme != "https":
                    errors.append(f"Vault URL must use HTTPS: {self.vault_url}")
                if not parsed.hostname or not parsed.hostname.endswith(".vault.azure.net"):
                    errors.append(
                        f"Invalid Azure Key Vault URL format. "
                        f"Hostname must end with '.vault.azure.net': {self.vault_url}"
                    )
            except Exception as e:
                errors.append(f"Invalid URL format: {self.vault_url} - {e}")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        # Lazy-load Azure client
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Get or create Azure Key Vault client.

        Returns:
            Initialized SecretClient instance

        Raises:
            PluginAPIError: If Azure libraries are not installed
        """
        if self._client is None:
            try:
                from azure.keyvault.secrets import (  # type: ignore[import-not-found]
                    SecretClient,
                )
            except ImportError as e:
                raise PluginAPIError(
                    self.metadata.name,
                    "azure-keyvault-secrets library not installed. "
                    "Install with: pip install azure-keyvault-secrets azure-identity",
                    original_error=e,
                ) from e

            # Create or get credential
            if self._credential is None:
                try:
                    from azure.identity import (  # type: ignore[import-not-found]
                        DefaultAzureCredential,
                    )

                    self._credential = DefaultAzureCredential()
                except ImportError as e:
                    raise PluginAPIError(
                        self.metadata.name,
                        "azure-identity library not installed. " "Install with: pip install azure-identity",
                        original_error=e,
                    ) from e

            # Create Secret Client
            self._client = SecretClient(vault_url=self.vault_url, credential=self._credential)

        return self._client

    def load(self) -> dict[str, str]:
        """Load secrets from Azure Key Vault.

        Retrieves all secrets from the Key Vault (or filtered by prefix) and
        converts them to environment variables.

        Azure Key Vault secret names use hyphens (-) by convention, while
        environment variables use underscores (_). This method automatically
        converts hyphens to underscores and converts to uppercase.

        Returns:
            Dictionary of environment variable name -> value mappings

        Raises:
            PluginAPIError: If Azure API call fails or authentication fails

        Example:
            >>> azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")
            >>> secrets = azure.load()
            >>> print(secrets)
            {'DATABASE_URL': 'postgresql://...', 'API_KEY': 'sk_...'}
        """
        try:
            env_vars: dict[str, str] = {}

            # List all secret properties (names and metadata)
            secret_properties = self.client.list_properties_of_secrets()

            for secret_property in secret_properties:
                secret_name = secret_property.name

                # Apply prefix filter if specified
                if self.secret_prefix and not secret_name.startswith(self.secret_prefix):
                    continue

                # Skip disabled secrets
                if not secret_property.enabled:
                    continue

                # Get secret value
                try:
                    secret = self.client.get_secret(secret_name)
                    secret_value = secret.value

                    if secret_value is not None:
                        # Convert Azure naming (hyphens) to env var naming (underscores)
                        env_var_name = self._sanitize_key(secret_name)
                        env_vars[env_var_name] = secret_value

                except Exception as e:
                    # Log individual secret failures but continue loading others
                    # This prevents one failed secret from breaking entire config load
                    continue

            return env_vars

        except Exception as e:
            # Wrap any exceptions in PluginAPIError
            if isinstance(e, PluginAPIError):
                raise
            raise PluginAPIError(
                self.metadata.name,
                f"Failed to load secrets from Azure Key Vault '{self.vault_url}': {str(e)}",
                original_error=e,
            ) from e

    def _sanitize_key(self, secret_name: str) -> str:
        """Convert Azure Key Vault secret name to environment variable name.

        Azure Key Vault names use hyphens and can be mixed case.
        Environment variables traditionally use uppercase with underscores.

        Args:
            secret_name: Azure Key Vault secret name

        Returns:
            Sanitized env var name (uppercase, underscores instead of hyphens)

        Example:
            >>> self._sanitize_key("database-url")
            'DATABASE_URL'
            >>> self._sanitize_key("myapp-api-key")
            'MYAPP_API_KEY'
        """
        # Remove prefix if specified
        if self.secret_prefix and secret_name.startswith(self.secret_prefix):
            secret_name = secret_name[len(self.secret_prefix) :]

        # Replace hyphens with underscores, uppercase
        sanitized = secret_name.replace("-", "_").upper()
        return sanitized

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Azure Key Vault plugin configuration.

        Args:
            config: Configuration dictionary with keys:
                - vault_url: Key Vault URL (required)
                - secret_prefix: (optional) Prefix filter for secrets
                - credential: (optional) Custom credential object

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid

        Example:
            >>> azure = AzureKeyVaultSource(vault_url="https://mykeyvault.vault.azure.net")
            >>> config = {"vault_url": "https://mykeyvault.vault.azure.net"}
            >>> azure.validate_config(config)
            True
        """
        errors: list[str] = []

        # Check required fields
        if "vault_url" not in config or not config["vault_url"]:
            errors.append("Missing required field: vault_url")
        else:
            vault_url = config["vault_url"]
            # Validate URL format with proper domain verification
            try:
                parsed = urlparse(vault_url)
                if parsed.scheme != "https":
                    errors.append(f"Vault URL must use HTTPS: {vault_url}")
                if not parsed.hostname or not parsed.hostname.endswith(".vault.azure.net"):
                    errors.append(
                        f"Invalid Azure Key Vault URL format. "
                        f"Hostname must end with '.vault.azure.net': {vault_url}"
                    )
            except Exception as e:
                errors.append(f"Invalid URL format: {vault_url} - {e}")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        return True
