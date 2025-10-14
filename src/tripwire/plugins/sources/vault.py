"""HashiCorp Vault plugin for TripWire.

This plugin enables reading secrets from HashiCorp Vault KV (Key-Value) secrets engine.
Supports both KV v1 and KV v2 engines with token-based authentication.

Dependencies:
    hvac>=2.0.0  # HashiCorp Vault API client

Installation:
    pip install hvac

Usage:
    >>> from tripwire.plugins.sources import VaultEnvSource
    >>> from tripwire import TripWire
    >>>
    >>> vault = VaultEnvSource(
    ...     url="https://vault.example.com",
    ...     token="hvs.CAESIxxx",  # Vault token
    ...     mount_point="secret",  # KV mount point
    ...     path="myapp/production",  # Path to secrets
    ...     kv_version=2  # KV engine version (1 or 2)
    ... )
    >>> env = TripWire(sources=[vault])

Environment Variables (Alternative to constructor args):
    VAULT_ADDR: Vault server URL
    VAULT_TOKEN: Vault authentication token
    VAULT_MOUNT_POINT: KV mount point (default: "secret")
    VAULT_PATH: Path to secrets within mount
    VAULT_KV_VERSION: KV engine version (default: 2)
"""

from __future__ import annotations

import os
import warnings
from typing import Any
from urllib.parse import urlparse

from tripwire.plugins.base import PluginInterface, PluginMetadata
from tripwire.plugins.errors import (
    PluginAPIError,
    PluginValidationError,
    SecurityWarning,
)


class VaultEnvSource(PluginInterface):
    """HashiCorp Vault secrets plugin.

    Reads environment variables from HashiCorp Vault KV secrets engine.
    Supports KV v1 and v2 with automatic version detection.

    Attributes:
        url: Vault server URL (e.g., "https://vault.example.com")
        token: Vault authentication token
        mount_point: KV secrets engine mount point (default: "secret")
        path: Path to secrets within the mount (e.g., "myapp/production")
        kv_version: KV engine version - 1 or 2 (default: 2)
        namespace: Vault namespace for multi-tenancy (Enterprise feature)
        verify_ssl: Verify SSL certificates (default: True)

    Example:
        >>> vault = VaultEnvSource(
        ...     url="https://vault.example.com",
        ...     token="hvs.xxx",
        ...     mount_point="secret",
        ...     path="myapp/config"
        ... )
        >>> secrets = vault.load()
        >>> print(secrets["DATABASE_URL"])
    """

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        mount_point: str = "secret",
        path: str | None = None,
        kv_version: int = 2,
        namespace: str | None = None,
        verify_ssl: bool = True,
        allow_http: bool = False,
    ) -> None:
        """Initialize Vault plugin.

        Args:
            url: Vault server URL (or set VAULT_ADDR env var)
            token: Vault token (or set VAULT_TOKEN env var)
            mount_point: KV mount point (default: "secret")
            path: Path to secrets (or set VAULT_PATH env var)
            kv_version: KV engine version - 1 or 2 (default: 2)
            namespace: Vault namespace (Enterprise)
            verify_ssl: Verify SSL certificates (default: True)
            allow_http: Allow HTTP for local/internal deployments (default: False).
                       When True, shows security warning. Use only for:
                       - Local development (localhost)
                       - Same-VM deployments
                       - Cluster-internal communication
                       NOT recommended for production or internet-facing deployments.

        Raises:
            PluginValidationError: If required parameters are missing or URL is invalid
        """
        metadata = PluginMetadata(
            name="vault",
            version="1.0.0",
            author="TripWire Team",
            description="HashiCorp Vault KV secrets integration",
            homepage="https://github.com/Daily-Nerd/TripWire",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["secrets", "vault", "hashicorp", "cloud"],
        )
        super().__init__(metadata)

        # Allow environment variables as fallback
        self.url = url or os.getenv("VAULT_ADDR")
        self.token = token or os.getenv("VAULT_TOKEN")
        self.mount_point = mount_point or os.getenv("VAULT_MOUNT_POINT", "secret")
        self.path = path or os.getenv("VAULT_PATH")
        self.kv_version = int(os.getenv("VAULT_KV_VERSION", str(kv_version)))
        self.namespace = namespace or os.getenv("VAULT_NAMESPACE")
        self.verify_ssl = verify_ssl
        self.allow_http = allow_http

        # Validate required parameters
        errors: list[str] = []
        if not self.url:
            errors.append("Vault URL is required (url parameter or VAULT_ADDR env var)")
        if not self.token:
            errors.append("Vault token is required (token parameter or VAULT_TOKEN env var)")
        if not self.path:
            errors.append("Vault path is required (path parameter or VAULT_PATH env var)")
        if self.kv_version not in (1, 2):
            errors.append(f"Invalid KV version: {self.kv_version} (must be 1 or 2)")

        # Security: Validate URL scheme - HTTPS by default, HTTP with opt-in
        if self.url:
            parsed = urlparse(self.url)

            if parsed.scheme == "http":
                if not self.allow_http:
                    errors.append(
                        "Vault URL must use HTTPS. If deploying locally/internally, "
                        "set allow_http=True (not recommended for production)"
                    )
                else:
                    # Show warning but allow HTTP
                    warnings.warn(
                        f"Security Warning: Using HTTP for Vault at {self.url}. "
                        f"This is insecure for production. Use HTTPS or ensure this is "
                        f"a local/internal deployment only.",
                        SecurityWarning,
                        stacklevel=2,
                    )
            elif parsed.scheme != "https":
                errors.append(f"Invalid URL scheme: {parsed.scheme}")

            if not parsed.hostname:
                errors.append(f"Invalid Vault URL format: {self.url}")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        # Lazy-load hvac client
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Get or create Vault client.

        Returns:
            Initialized hvac.Client instance

        Raises:
            PluginAPIError: If hvac library is not installed
        """
        if self._client is None:
            try:
                import hvac  # type: ignore[import-untyped]
            except ImportError as e:
                raise PluginAPIError(
                    self.metadata.name,
                    "hvac library not installed. Install with: pip install hvac",
                    original_error=e,
                ) from e

            self._client = hvac.Client(
                url=self.url,
                token=self.token,
                namespace=self.namespace,
                verify=self.verify_ssl,
            )

        return self._client

    def load(self) -> dict[str, str]:
        """Load secrets from Vault KV store.

        Reads all key-value pairs from the specified Vault path and returns
        them as environment variables.

        Returns:
            Dictionary of environment variable name -> value mappings

        Raises:
            PluginAPIError: If Vault API call fails or authentication fails

        Example:
            >>> vault = VaultEnvSource(url="...", token="...", path="myapp/config")
            >>> secrets = vault.load()
            >>> print(secrets)
            {'DATABASE_URL': 'postgresql://...', 'API_KEY': 'sk_...'}
        """
        try:
            # Verify authentication
            if not self.client.is_authenticated():
                raise PluginAPIError(
                    self.metadata.name,
                    f"Vault authentication failed. Token may be invalid or expired.",
                )

            # Read secrets based on KV version
            if self.kv_version == 2:
                # KV v2 has versioned secrets with 'data' wrapper
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=self.path,
                    mount_point=self.mount_point,
                )
                # KV v2 response structure: response['data']['data']
                secrets = response.get("data", {}).get("data", {})
            else:
                # KV v1 has simple key-value storage
                response = self.client.secrets.kv.v1.read_secret(
                    path=self.path,
                    mount_point=self.mount_point,
                )
                # KV v1 response structure: response['data']
                secrets = response.get("data", {})

            # Convert all values to strings (TripWire expects string values)
            env_vars: dict[str, str] = {}
            for key, value in secrets.items():
                if isinstance(value, (str, int, float, bool)):
                    env_vars[key] = str(value)
                else:
                    # Skip complex types (lists, dicts) as they can't be env vars
                    continue

            return env_vars

        except Exception as e:
            # Wrap any exceptions in PluginAPIError
            if isinstance(e, PluginAPIError):
                raise
            raise PluginAPIError(
                self.metadata.name,
                f"Failed to load secrets from Vault path '{self.path}': {str(e)}",
                original_error=e,
            ) from e

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Vault plugin configuration.

        Args:
            config: Configuration dictionary with keys:
                - url: Vault server URL
                - token: Vault authentication token
                - path: Path to secrets
                - mount_point: (optional) KV mount point
                - kv_version: (optional) KV version (1 or 2)

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid

        Example:
            >>> vault = VaultEnvSource(url="...", token="...", path="...")
            >>> config = {
            ...     "url": "https://vault.example.com",
            ...     "token": "hvs.xxx",
            ...     "path": "myapp/config"
            ... }
            >>> vault.validate_config(config)
            True
        """
        errors: list[str] = []

        # Check required fields
        required_fields = ["url", "token", "path"]
        for field in required_fields:
            if field not in config or not config[field]:
                errors.append(f"Missing required field: {field}")

        # Validate KV version if provided
        if "kv_version" in config:
            kv_version = config["kv_version"]
            if kv_version not in (1, 2, "1", "2"):
                errors.append(f"Invalid kv_version: {kv_version} (must be 1 or 2)")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        return True
