"""AWS Secrets Manager plugin for TripWire.

This plugin enables reading secrets from AWS Secrets Manager with support for
multiple authentication methods (IAM roles, credentials, profiles).

Dependencies:
    boto3>=1.34.0  # AWS SDK for Python

Installation:
    pip install boto3 OR uv add boto3

Usage:
    >>> from tripwire.plugins.sources import AWSSecretsSource
    >>> from tripwire import TripWire
    >>>
    >>> aws = AWSSecretsSource(
    ...     secret_name="myapp/production/config",
    ...     region_name="us-east-1"
    ... )
    >>> env = TripWire(sources=[aws])

Authentication (in order of precedence):
    1. Explicit credentials (access_key_id + secret_access_key)
    2. AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY environment variables
    3. AWS credentials file (~/.aws/credentials)
    4. IAM role (when running on EC2, ECS, Lambda, etc.)
    5. AWS profile (AWS_PROFILE environment variable)

Environment Variables:
    AWS_REGION: AWS region (overrides region_name parameter)
    AWS_SECRET_NAME: Secret name or ARN
    AWS_PROFILE: AWS credentials profile name
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
"""

from __future__ import annotations

import json
import os
from typing import Any

from tripwire.plugins.base import PluginInterface, PluginMetadata
from tripwire.plugins.errors import PluginAPIError, PluginValidationError


class AWSSecretsSource(PluginInterface):
    """AWS Secrets Manager plugin.

    Reads environment variables from AWS Secrets Manager. Supports both
    secret strings and JSON-encoded secrets.

    Attributes:
        secret_name: Secret name or ARN in Secrets Manager
        region_name: AWS region (e.g., "us-east-1")
        profile_name: AWS credentials profile name (optional)
        access_key_id: AWS access key ID (optional, for explicit credentials)
        secret_access_key: AWS secret access key (optional)
        parse_json: Parse JSON secrets into individual env vars (default: True)

    Example:
        >>> aws = AWSSecretsSource(
        ...     secret_name="myapp/production",
        ...     region_name="us-east-1"
        ... )
        >>> secrets = aws.load()
        >>> print(secrets["DATABASE_URL"])
    """

    def __init__(
        self,
        secret_name: str | None = None,
        region_name: str | None = None,
        profile_name: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        parse_json: bool = True,
    ) -> None:
        """Initialize AWS Secrets Manager plugin.

        Args:
            secret_name: Secret name or ARN (or set AWS_SECRET_NAME env var)
            region_name: AWS region (or set AWS_REGION env var)
            profile_name: AWS profile name (or set AWS_PROFILE env var)
            access_key_id: AWS access key (or set AWS_ACCESS_KEY_ID env var)
            secret_access_key: AWS secret key (or set AWS_SECRET_ACCESS_KEY env var)
            parse_json: Parse JSON secrets into separate env vars (default: True)

        Raises:
            PluginValidationError: If required parameters are missing
        """
        metadata = PluginMetadata(
            name="aws-secrets",
            version="1.0.0",
            author="TripWire Team",
            description="AWS Secrets Manager integration",
            homepage="https://github.com/Daily-Nerd/TripWire",
            license="MIT",
            min_tripwire_version="0.10.0",
            tags=["secrets", "aws", "cloud", "amazon"],
        )
        super().__init__(metadata)

        # Allow environment variables as fallback
        self.secret_name = secret_name or os.getenv("AWS_SECRET_NAME")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.profile_name = profile_name or os.getenv("AWS_PROFILE")
        self.access_key_id = access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_access_key = secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.parse_json = parse_json

        # Validate required parameters
        errors: list[str] = []
        if not self.secret_name:
            errors.append("Secret name is required (secret_name parameter or AWS_SECRET_NAME env var)")
        if not self.region_name:
            errors.append("AWS region is required (region_name parameter or AWS_REGION env var)")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        # Lazy-load boto3 client
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        """Get or create AWS Secrets Manager client.

        Returns:
            Initialized boto3 SecretsManager client

        Raises:
            PluginAPIError: If boto3 library is not installed
        """
        if self._client is None:
            try:
                import boto3  # type: ignore[import-not-found]
            except ImportError as e:
                raise PluginAPIError(
                    self.metadata.name,
                    "boto3 library not installed. Install with: pip install boto3",
                    original_error=e,
                ) from e

            # Build session kwargs
            session_kwargs: dict[str, Any] = {}
            if self.profile_name:
                session_kwargs["profile_name"] = self.profile_name

            # Create session
            session = boto3.Session(**session_kwargs)

            # Build client kwargs
            client_kwargs: dict[str, Any] = {"region_name": self.region_name}
            if self.access_key_id and self.secret_access_key:
                client_kwargs["aws_access_key_id"] = self.access_key_id
                client_kwargs["aws_secret_access_key"] = self.secret_access_key

            # Create Secrets Manager client
            self._client = session.client("secretsmanager", **client_kwargs)

        return self._client

    def load(self) -> dict[str, str]:
        """Load secrets from AWS Secrets Manager.

        Retrieves the secret value and parses it based on format:
        - JSON secrets: Parsed into individual env vars (if parse_json=True)
        - String secrets: Returned as single env var with secret name as key

        Returns:
            Dictionary of environment variable name -> value mappings

        Raises:
            PluginAPIError: If AWS API call fails or secret not found

        Example:
            >>> aws = AWSSecretsSource(secret_name="myapp/config", region_name="us-east-1")
            >>> secrets = aws.load()
            >>> print(secrets)
            {'DATABASE_URL': 'postgresql://...', 'API_KEY': 'sk_...'}
        """
        try:
            # Get secret value from AWS
            response = self.client.get_secret_value(SecretId=self.secret_name)

            # Extract secret string
            secret_string = response.get("SecretString")
            if not secret_string:
                # Secret might be binary (not supported for env vars)
                raise PluginAPIError(
                    self.metadata.name,
                    f"Secret '{self.secret_name}' contains binary data, not a string. "
                    "Only string secrets are supported for environment variables.",
                )

            # Parse secret based on format
            env_vars: dict[str, str] = {}

            if self.parse_json:
                try:
                    # Try to parse as JSON
                    secret_data = json.loads(secret_string)

                    if isinstance(secret_data, dict):
                        # JSON object - expand into individual env vars
                        for key, value in secret_data.items():
                            if isinstance(value, (str, int, float, bool)):
                                env_vars[key] = str(value)
                            else:
                                # Skip complex nested structures
                                continue
                    else:
                        # JSON but not an object (array, primitive)
                        # Fall back to string representation
                        env_vars[self._sanitize_key(self.secret_name)] = str(secret_data)

                except json.JSONDecodeError:
                    # Not JSON - treat as plain string
                    env_vars[self._sanitize_key(self.secret_name)] = secret_string
            else:
                # Don't parse JSON - treat as plain string
                env_vars[self._sanitize_key(self.secret_name)] = secret_string

            return env_vars

        except Exception as e:
            # Wrap any exceptions in PluginAPIError
            if isinstance(e, PluginAPIError):
                raise
            raise PluginAPIError(
                self.metadata.name,
                f"Failed to load secret '{self.secret_name}' from AWS Secrets Manager: {str(e)}",
                original_error=e,
            ) from e

    def _sanitize_key(self, secret_name: str | None) -> str:
        """Sanitize secret name to be a valid environment variable name.

        Args:
            secret_name: AWS secret name or ARN

        Returns:
            Sanitized env var name (uppercase, alphanumeric + underscores)

        Raises:
            PluginValidationError: If secret_name is None

        Example:
            >>> self._sanitize_key("myapp/production/db-config")
            'MYAPP_PRODUCTION_DB_CONFIG'
        """
        if secret_name is None:
            raise PluginValidationError(self.metadata.name, ["Secret name cannot be None"])

        # Extract name from ARN if needed
        if ":" in secret_name:
            # ARN format: arn:aws:secretsmanager:region:account:secret:name-xxxxx
            parts = secret_name.split(":")
            if len(parts) >= 7:
                secret_name = parts[-1]
                # Remove version suffix if present
                secret_name = secret_name.rsplit("-", 1)[0]

        # Replace non-alphanumeric characters with underscores for env var compatibility
        sanitized = "".join(c if c.isalnum() else "_" for c in secret_name)
        return sanitized.upper()

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate AWS Secrets Manager plugin configuration.

        Args:
            config: Configuration dictionary with keys:
                - secret_name: Secret name or ARN (required)
                - region_name: AWS region (required)
                - profile_name: (optional) AWS profile
                - access_key_id: (optional) AWS access key
                - secret_access_key: (optional) AWS secret key

        Returns:
            True if configuration is valid

        Raises:
            PluginValidationError: If configuration is invalid

        Example:
            >>> aws = AWSSecretsSource(secret_name="myapp/config", region_name="us-east-1")
            >>> config = {
            ...     "secret_name": "myapp/production",
            ...     "region_name": "us-east-1"
            ... }
            >>> aws.validate_config(config)
            True
        """
        errors: list[str] = []

        # Check required fields
        if "secret_name" not in config or not config["secret_name"]:
            errors.append("Missing required field: secret_name")
        if "region_name" not in config or not config["region_name"]:
            errors.append("Missing required field: region_name")

        # Validate explicit credentials (both or neither)
        has_access_key = "access_key_id" in config and config["access_key_id"]
        has_secret_key = "secret_access_key" in config and config["secret_access_key"]
        if has_access_key != has_secret_key:
            errors.append("Both access_key_id and secret_access_key must be provided together")

        if errors:
            raise PluginValidationError(self.metadata.name, errors)

        return True
