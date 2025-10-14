"""Remote HTTP configuration source plugin for TripWire.

This plugin enables reading configuration from any HTTP/REST API endpoint
that returns JSON or YAML formatted data. Supports authentication via
API keys, bearer tokens, or custom headers.

Dependencies:
    requests>=2.31.0  # HTTP library
    pyyaml>=6.0.0  # YAML parsing (optional, for YAML responses)

Installation:
    pip install requests
    pip install pyyaml  # Optional, for YAML support

Usage:
    >>> from tripwire.plugins.sources import RemoteConfigSource
    >>> from tripwire import TripWire
    >>>
    >>> remote = RemoteConfigSource(
    ...     url="https://config.example.com/api/config",
    ...     headers={"Authorization": "Bearer token123"},
    ...     format="json"
    ... )
    >>> env = TripWire(sources=[remote])

Environment Variables:
    REMOTE_CONFIG_URL: Configuration endpoint URL
    REMOTE_CONFIG_API_KEY: API key for authentication
    REMOTE_CONFIG_FORMAT: Response format (json or yaml)
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


class RemoteConfigSource(PluginInterface):
    """Remote HTTP configuration source plugin.

    Fetches configuration from HTTP endpoints supporting JSON or YAML responses.
    Ideal for centralized configuration management systems.

    Attributes:
        url: Configuration API endpoint URL
        format: Response format - "json" or "yaml" (default: "json")
        headers: HTTP headers for authentication/authorization
        timeout: Request timeout in seconds (default: 30)
        verify_ssl: Verify SSL certificates (default: True)
        api_key_header: Header name for API key (default: "X-API-Key")
        api_key: API key value (alternative to manual headers)

    Example:
        >>> # Using custom headers
        >>> remote = RemoteConfigSource(
        ...     url="https://config.example.com/myapp",
        ...     headers={"Authorization": "Bearer token123"}
        ... )
        >>>
        >>> # Using API key
        >>> remote = RemoteConfigSource(
        ...     url="https://config.example.com/myapp",
        ...     api_key="secret123",
        ...     api_key_header="X-API-Key"
        ... )
        >>>
        >>> secrets = remote.load()
    """

    def __init__(
        self,
        url: str | None = None,
        format: str = "json",
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        api_key: str | None = None,
        api_key_header: str = "X-API-Key",
        allow_http: bool = False,
    ) -> None:
        """Initialize Remote Config plugin.

        Args:
            url: API endpoint URL (or set REMOTE_CONFIG_URL env var)
            format: Response format - "json" or "yaml" (default: "json")
            headers: Custom HTTP headers for authentication
            timeout: Request timeout in seconds (default: 30)
            verify_ssl: Verify SSL certificates (default: True)
            api_key: API key value (or set REMOTE_CONFIG_API_KEY env var)
            api_key_header: Header name for API key (default: "X-API-Key")
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
            name="remote-config",
            version="1.0.0",
            author="TripWire Team",
            description="Generic HTTP/REST API configuration source",
            homepage="https://github.com/Daily-Nerd/TripWire",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["config", "remote", "http", "api"],
        )
        super().__init__(metadata)

        # Allow environment variables as fallback
        self.url = url or os.getenv("REMOTE_CONFIG_URL")
        self.format = (os.getenv("REMOTE_CONFIG_FORMAT") or format).lower()
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.api_key = api_key or os.getenv("REMOTE_CONFIG_API_KEY")
        self.api_key_header = api_key_header
        self.allow_http = allow_http

        # Build headers
        self.headers = headers or {}
        if self.api_key:
            self.headers[self.api_key_header] = self.api_key

        # Validate required parameters
        errors: list[str] = []
        if not self.url:
            errors.append("URL is required (url parameter or REMOTE_CONFIG_URL env var)")
        if self.format not in ("json", "yaml"):
            errors.append(f"Invalid format: {self.format} (must be 'json' or 'yaml')")

        # Security: Validate URL scheme - HTTPS by default, HTTP with opt-in
        if self.url:
            parsed = urlparse(self.url)

            if parsed.scheme == "http":
                if not self.allow_http:
                    errors.append(
                        "Remote config URL must use HTTPS. If deploying locally/internally, "
                        "set allow_http=True (not recommended for production)"
                    )
                else:
                    # Show warning but allow HTTP
                    warnings.warn(
                        f"Security Warning: Using HTTP for remote config at {self.url}. "
                        f"This is insecure for production. Use HTTPS or ensure this is "
                        f"a local/internal deployment only.",
                        SecurityWarning,
                        stacklevel=2,
                    )
            elif parsed.scheme != "https":
                errors.append(f"Invalid URL scheme: {parsed.scheme}")

            if not parsed.hostname:
                errors.append(f"Invalid remote config URL format: {self.url}")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

    def load(self) -> dict[str, str]:
        """Load configuration from remote HTTP endpoint.

        Fetches configuration via HTTP GET request and parses the response
        based on the specified format (JSON or YAML).

        Returns:
            Dictionary of environment variable name -> value mappings

        Raises:
            PluginAPIError: If HTTP request fails, parsing fails, or response is invalid

        Example:
            >>> remote = RemoteConfigSource(
            ...     url="https://config.example.com/myapp",
            ...     headers={"Authorization": "Bearer token"}
            ... )
            >>> config = remote.load()
            >>> print(config)
            {'DATABASE_URL': 'postgresql://...', 'API_KEY': 'sk_...'}
        """
        try:
            # Import requests
            try:
                import requests  # type: ignore[import-untyped]
            except ImportError as e:
                raise PluginAPIError(
                    self.metadata.name,
                    "requests library not installed. Install with: pip install requests",
                    original_error=e,
                ) from e

            # Make HTTP request
            try:
                response = requests.get(
                    self.url,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
                response.raise_for_status()  # Raise HTTPError for bad status codes
            except requests.exceptions.RequestException as e:
                raise PluginAPIError(
                    self.metadata.name,
                    f"HTTP request to '{self.url}' failed: {str(e)}",
                    original_error=e,
                ) from e

            # Parse response based on format
            try:
                if self.format == "json":
                    data = response.json()
                elif self.format == "yaml":
                    try:
                        import yaml
                    except ImportError as e:
                        raise PluginAPIError(
                            self.metadata.name,
                            "pyyaml library not installed. Install with: pip install pyyaml",
                            original_error=e,
                        ) from e
                    data = yaml.safe_load(response.text)
                else:
                    raise PluginAPIError(
                        self.metadata.name,
                        f"Unsupported format: {self.format}",
                    )
            except Exception as e:
                raise PluginAPIError(
                    self.metadata.name,
                    f"Failed to parse {self.format.upper()} response from '{self.url}': {str(e)}",
                    original_error=e,
                ) from e

            # Convert parsed data to env vars
            if not isinstance(data, dict):
                raise PluginAPIError(
                    self.metadata.name,
                    f"Response must be a JSON/YAML object (dict), got {type(data).__name__}",
                )

            env_vars: dict[str, str] = {}
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    env_vars[key] = str(value)
                elif value is None:
                    # Skip null values
                    continue
                else:
                    # Skip complex nested structures (lists, dicts)
                    continue

            return env_vars

        except Exception as e:
            # Wrap any exceptions in PluginAPIError
            if isinstance(e, PluginAPIError):
                raise
            raise PluginAPIError(
                self.metadata.name,
                f"Failed to load configuration from '{self.url}': {str(e)}",
                original_error=e,
            ) from e

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Remote Config plugin configuration.

        Args:
            config: Configuration dictionary with keys:
                - url: API endpoint URL (required)
                - format: Response format - "json" or "yaml" (optional, default: "json")
                - headers: HTTP headers (optional)
                - timeout: Request timeout (optional, default: 30)
                - api_key: API key (optional)

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid

        Example:
            >>> remote = RemoteConfigSource(url="https://config.example.com/myapp")
            >>> config = {
            ...     "url": "https://config.example.com/myapp",
            ...     "format": "json",
            ...     "headers": {"Authorization": "Bearer token"}
            ... }
            >>> remote.validate_config(config)
            True
        """
        errors: list[str] = []

        # Check required fields
        if "url" not in config or not config["url"]:
            errors.append("Missing required field: url")
        else:
            url = config["url"]
            allow_http = config.get("allow_http", False)

            # Security: Validate URL scheme - HTTPS by default, HTTP with opt-in
            parsed = urlparse(url)

            if parsed.scheme == "http":
                if not allow_http:
                    errors.append(
                        "Remote config URL must use HTTPS. If deploying locally/internally, "
                        "set allow_http=True (not recommended for production)"
                    )
            elif parsed.scheme != "https":
                errors.append(f"Invalid URL scheme: {parsed.scheme}")

            if not parsed.hostname:
                errors.append(f"Invalid remote config URL format: {url}")

        # Validate format if provided
        if "format" in config:
            fmt = config["format"].lower() if isinstance(config["format"], str) else config["format"]
            if fmt not in ("json", "yaml"):
                errors.append(f"Invalid format: {fmt} (must be 'json' or 'yaml')")

        # Validate timeout if provided
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append(f"Invalid timeout: {timeout} (must be positive number)")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        return True
