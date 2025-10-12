"""Official TripWire plugin sources for secrets management.

This package contains official plugins for integrating TripWire with
popular secrets management services and configuration backends.

Available Plugins:
    - VaultEnvSource: HashiCorp Vault KV store integration
    - AWSSecretsSource: AWS Secrets Manager integration
    - AzureKeyVaultSource: Azure Key Vault integration
    - RemoteConfigSource: Generic HTTP/REST API configuration source

Usage:
    >>> from tripwire.plugins.sources import VaultEnvSource
    >>> from tripwire import TripWire
    >>>
    >>> # Register and use Vault plugin
    >>> vault = VaultEnvSource(
    ...     url="https://vault.example.com",
    ...     token="hvs.xxx",
    ...     mount_point="secret",
    ...     path="myapp/config"
    ... )
    >>> env = TripWire(sources=[vault])
"""

from tripwire.plugins.sources.aws_secrets import AWSSecretsSource
from tripwire.plugins.sources.azure_keyvault import AzureKeyVaultSource
from tripwire.plugins.sources.remote_config import RemoteConfigSource
from tripwire.plugins.sources.vault import VaultEnvSource

__all__ = [
    "VaultEnvSource",
    "AWSSecretsSource",
    "AzureKeyVaultSource",
    "RemoteConfigSource",
]
