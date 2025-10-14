"""Security module for TripWire.

This module provides security features for protecting sensitive environment
variables from accidental exposure.

Components:
    - Secret wrapper: Prevents accidental leakage through print(), logging, JSON, etc.
    - Logging integration: Automatic secret redaction in log output
    - Pattern detection: Regex-based secret detection for defense-in-depth

Example:
    >>> from tripwire.security import Secret, register_secret, auto_install
    >>>
    >>> # Wrap sensitive values
    >>> api_key: Secret[str] = Secret("my_api_key")
    >>> print(api_key)  # Output: **********
    >>>
    >>> # Enable automatic logging redaction
    >>> auto_install()
    >>> register_secret("my_password")
    >>>
    >>> import logging
    >>> logging.info("Password: my_password")
    >>> # Output: Password: **********
"""

from tripwire.security.logging import (
    COMMON_SECRET_PATTERNS,
    SecretRedactionFilter,
    SecretRedactionFormatter,
    auto_install,
    auto_uninstall,
    clear_registry,
    register_common_patterns,
    register_pattern,
    register_secret,
    unregister_secret,
)
from tripwire.security.secret import (
    MASK_STRING,
    Secret,
    SecretBytes,
    SecretJSONEncoder,
    SecretStr,
    StrictSecretJSONEncoder,
    is_secret,
    mask_multiple_secrets,
    mask_secret_in_string,
    unwrap_secret,
)

__all__ = [
    # Secret wrapper
    "Secret",
    "SecretStr",
    "SecretBytes",
    "MASK_STRING",
    # JSON encoders
    "SecretJSONEncoder",
    "StrictSecretJSONEncoder",
    # Utilities
    "is_secret",
    "unwrap_secret",
    "mask_secret_in_string",
    "mask_multiple_secrets",
    # Logging integration
    "SecretRedactionFilter",
    "SecretRedactionFormatter",
    "register_secret",
    "unregister_secret",
    "register_pattern",
    "clear_registry",
    "auto_install",
    "auto_uninstall",
    "register_common_patterns",
    "COMMON_SECRET_PATTERNS",
]
