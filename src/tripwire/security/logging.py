"""Logging integration for automatic secret redaction.

This module provides logging filters and handlers that automatically redact
secrets from log output, preventing accidental exposure through application logs.

Features:
    - Automatic redaction of registered secrets
    - Pattern-based detection for common secret formats
    - Thread-safe secret registry
    - Easy integration with Python's logging module

Example:
    >>> import logging
    >>> from tripwire.security.logging import SecretRedactionFilter, register_secret
    >>>
    >>> # Register a secret for redaction
    >>> register_secret("my_secret_token")
    >>>
    >>> # Add filter to logger
    >>> handler = logging.StreamHandler()
    >>> handler.addFilter(SecretRedactionFilter())
    >>> logger = logging.getLogger("myapp")
    >>> logger.addHandler(handler)
    >>>
    >>> # Secrets are automatically redacted
    >>> logger.info("Using token: my_secret_token")
    >>> # Output: Using token: **********
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Literal, Optional, Pattern, Set

from tripwire.security.secret import MASK_STRING, Secret, unwrap_secret

# Global registry of secrets to redact (thread-safe)
_secret_registry_lock = threading.Lock()
_registered_secrets: Set[str] = set()
_registered_patterns: list[Pattern[str]] = []


def register_secret(secret: str | Secret[str]) -> None:
    """Register a secret value for automatic redaction in logs.

    Once registered, any occurrence of this secret in log messages will be
    automatically replaced with a mask (default: "**********").

    Args:
        secret: The secret value to register (string or Secret wrapper)

    Thread Safety:
        This function is thread-safe and can be called from multiple threads.

    Example:
        >>> from tripwire.security.logging import register_secret
        >>> register_secret("my_api_key_12345")
        >>>
        >>> # Now this secret will be redacted in all logs
        >>> import logging
        >>> logging.info("API Key: my_api_key_12345")
        >>> # Output: API Key: **********
    """
    # Unwrap Secret if provided
    actual_value = unwrap_secret(secret)

    if not actual_value:
        return  # Don't register empty strings

    with _secret_registry_lock:
        _registered_secrets.add(actual_value)


def unregister_secret(secret: str | Secret[str]) -> None:
    """Unregister a secret from automatic redaction.

    Args:
        secret: The secret value to unregister

    Thread Safety:
        This function is thread-safe.

    Example:
        >>> from tripwire.security.logging import register_secret, unregister_secret
        >>> register_secret("temp_token")
        >>> unregister_secret("temp_token")
    """
    actual_value = unwrap_secret(secret)

    with _secret_registry_lock:
        _registered_secrets.discard(actual_value)


def register_pattern(pattern: str | Pattern[str]) -> None:
    """Register a regex pattern for automatic secret detection and redaction.

    This is useful for redacting secrets that match a pattern (e.g., all AWS keys)
    without needing to register individual values.

    Args:
        pattern: Regex pattern to match secrets (string or compiled pattern)

    Example:
        >>> from tripwire.security.logging import register_pattern
        >>> # Redact all AWS access keys
        >>> register_pattern(r'AKIA[0-9A-Z]{16}')
        >>>
        >>> import logging
        >>> logging.info("Using key: AKIAIOSFODNN7EXAMPLE")
        >>> # Output: Using key: **********
    """
    compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    with _secret_registry_lock:
        _registered_patterns.append(compiled_pattern)


def clear_registry() -> None:
    """Clear all registered secrets and patterns.

    This is primarily for testing purposes.

    Thread Safety:
        This function is thread-safe.
    """
    with _secret_registry_lock:
        _registered_secrets.clear()
        _registered_patterns.clear()


class SecretRedactionFilter(logging.Filter):
    """Logging filter that redacts secrets from log messages.

    This filter automatically redacts:
    1. Registered secret values (via register_secret())
    2. Pattern-matched secrets (via register_pattern())
    3. Secret objects (automatically unwrapped and redacted)

    The filter operates on the log message AFTER formatting, so it catches
    secrets in f-strings, format strings, and concatenated messages.

    Thread Safety:
        This filter is thread-safe and can be used in multi-threaded applications.

    Example:
        >>> import logging
        >>> from tripwire.security.logging import SecretRedactionFilter, register_secret
        >>>
        >>> # Setup logging with redaction
        >>> handler = logging.StreamHandler()
        >>> handler.addFilter(SecretRedactionFilter())
        >>> logger = logging.getLogger("myapp")
        >>> logger.addHandler(handler)
        >>> logger.setLevel(logging.INFO)
        >>>
        >>> # Register secrets
        >>> register_secret("my_password_123")
        >>>
        >>> # Secrets are automatically redacted
        >>> logger.info("Password: my_password_123")
        >>> # Output: Password: **********

    Usage with TripWire:
        >>> from tripwire import TripWire
        >>> from tripwire.security.logging import SecretRedactionFilter, auto_install
        >>>
        >>> # Automatically install on all loggers
        >>> auto_install()
        >>>
        >>> env = TripWire(strict_secrets=True)
        >>> API_KEY: Secret[str] = env.require("API_KEY", secret=True)
        >>> # API_KEY is automatically registered for redaction
    """

    def __init__(
        self,
        mask: str = MASK_STRING,
        redact_secrets: bool = True,
        redact_patterns: bool = True,
    ) -> None:
        """Initialize the redaction filter.

        Args:
            mask: The string to replace secrets with (default: "**********")
            redact_secrets: Whether to redact registered secrets (default: True)
            redact_patterns: Whether to redact pattern-matched secrets (default: True)
        """
        super().__init__()
        self.mask = mask
        self.redact_secrets = redact_secrets
        self.redact_patterns = redact_patterns

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter a log record to redact secrets.

        Args:
            record: The log record to filter

        Returns:
            True (always allows the record through, just modifies the message)

        Note:
            This method modifies the record's message in-place to redact secrets.
            It also redacts secrets from exception information (tracebacks, exc_info).
        """
        # Get the formatted message (after f-strings, format(), etc.)
        original_msg = record.getMessage()

        # Redact registered secrets (exact string matching)
        if self.redact_secrets:
            with _secret_registry_lock:
                # Copy the set to avoid holding the lock during replacement
                secrets_to_redact = _registered_secrets.copy()

            # Sort by length (longest first) to handle substring secrets correctly
            # Example: If both "abc123" and "abc" are secrets, redact "abc123" first
            for secret_value in sorted(secrets_to_redact, key=len, reverse=True):
                if secret_value in original_msg:
                    original_msg = original_msg.replace(secret_value, self.mask)

        # Redact pattern-matched secrets (regex matching)
        if self.redact_patterns:
            with _secret_registry_lock:
                # Copy the list to avoid holding the lock during regex operations
                patterns_to_check = _registered_patterns.copy()

            for pattern in patterns_to_check:
                original_msg = pattern.sub(self.mask, original_msg)

        # Update the record's message if it changed
        if original_msg != record.getMessage():
            # Update both msg and args to prevent re-formatting from undoing redaction
            record.msg = original_msg
            record.args = ()  # Clear args since we already formatted

        # Redact exception information (critical for security)
        # This handles logger.exception() calls that include exc_info
        if record.exc_info:
            import traceback

            # Format the exception into text
            exc_text = "".join(traceback.format_exception(*record.exc_info))

            # Redact secrets from exception text
            if self.redact_secrets:
                with _secret_registry_lock:
                    secrets_to_redact = _registered_secrets.copy()

                for secret_value in sorted(secrets_to_redact, key=len, reverse=True):
                    if secret_value in exc_text:
                        exc_text = exc_text.replace(secret_value, self.mask)

            # Redact pattern-matched secrets from exception text
            if self.redact_patterns:
                with _secret_registry_lock:
                    patterns_to_check = _registered_patterns.copy()

                for pattern in patterns_to_check:
                    exc_text = pattern.sub(self.mask, exc_text)

            # Store the redacted exception text
            record.exc_text = exc_text
            # Clear exc_info to prevent double formatting
            # (the formatted text is already in exc_text)
            record.exc_info = None

        return True  # Always allow the record through


class SecretRedactionFormatter(logging.Formatter):
    """Logging formatter that redacts secrets from log output.

    This is an alternative to SecretRedactionFilter that works as a formatter
    instead of a filter. Use this if you need more control over formatting.

    Example:
        >>> import logging
        >>> from tripwire.security.logging import SecretRedactionFormatter
        >>>
        >>> handler = logging.StreamHandler()
        >>> formatter = SecretRedactionFormatter(
        ...     fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ... )
        >>> handler.setFormatter(formatter)
        >>> logger = logging.getLogger("myapp")
        >>> logger.addHandler(handler)
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: Literal["%", "{", "$"] = "%",
        mask: str = MASK_STRING,
    ) -> None:
        """Initialize the redaction formatter.

        Args:
            fmt: Format string (see logging.Formatter)
            datefmt: Date format string (see logging.Formatter)
            style: Format style (%, {, or $)
            mask: The string to replace secrets with
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.mask = mask

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record and redact secrets.

        Args:
            record: The log record to format

        Returns:
            Formatted and redacted log message
        """
        # Format using parent formatter
        formatted = super().format(record)

        # Redact secrets (same logic as SecretRedactionFilter)
        with _secret_registry_lock:
            secrets_to_redact = _registered_secrets.copy()
            patterns_to_check = _registered_patterns.copy()

        # Redact exact matches
        for secret_value in sorted(secrets_to_redact, key=len, reverse=True):
            if secret_value in formatted:
                formatted = formatted.replace(secret_value, self.mask)

        # Redact pattern matches
        for pattern in patterns_to_check:
            formatted = pattern.sub(self.mask, formatted)

        return formatted


def auto_install(
    logger_name: Optional[str] = None,
    mask: str = MASK_STRING,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Automatically install secret redaction on a logger.

    This is a convenience function to quickly add redaction to your application.

    Args:
        logger_name: Name of logger to install on (None = root logger)
        mask: The mask to use for redacted secrets
        handler: Specific handler to add filter to (None = all handlers)

    Example:
        >>> from tripwire.security.logging import auto_install
        >>>
        >>> # Install on root logger (affects all loggers)
        >>> auto_install()
        >>>
        >>> # Install on specific logger
        >>> auto_install("myapp")
        >>>
        >>> # Install on specific handler
        >>> import logging
        >>> handler = logging.StreamHandler()
        >>> auto_install(handler=handler)
    """
    redaction_filter = SecretRedactionFilter(mask=mask)

    if handler:
        # Install on specific handler
        handler.addFilter(redaction_filter)
    else:
        # Install on logger's handlers
        target_logger = logging.getLogger(logger_name)

        # Add filter to all existing handlers
        for existing_handler in target_logger.handlers:
            existing_handler.addFilter(redaction_filter)

        # If no handlers exist, add a default StreamHandler
        if not target_logger.handlers:
            default_handler = logging.StreamHandler()
            default_handler.addFilter(redaction_filter)
            target_logger.addHandler(default_handler)


def auto_uninstall(
    logger_name: Optional[str] = None,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Remove secret redaction from a logger.

    Args:
        logger_name: Name of logger to remove from (None = root logger)
        handler: Specific handler to remove filter from (None = all handlers)
    """
    if handler:
        # Remove from specific handler
        for filt in handler.filters[:]:  # Copy list to avoid mutation during iteration
            if isinstance(filt, SecretRedactionFilter):
                handler.removeFilter(filt)
    else:
        # Remove from logger's handlers
        target_logger = logging.getLogger(logger_name)
        for existing_handler in target_logger.handlers:
            for filt in existing_handler.filters[:]:
                if isinstance(filt, SecretRedactionFilter):
                    existing_handler.removeFilter(filt)


# Common secret patterns (can be registered automatically)
COMMON_SECRET_PATTERNS = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret_key": r"(?i)aws(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]",
    "github_token": r"ghp_[0-9a-zA-Z]{36}",
    "slack_token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[0-9a-zA-Z]{24,}",
    "stripe_key": r"sk_live_[0-9a-zA-Z]{24,}",
    "generic_api_key": r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"]?[0-9a-zA-Z]{32,}['\"]?",
    "generic_token": r"(?i)token['\"]?\s*[:=]\s*['\"]?[0-9a-zA-Z]{32,}['\"]?",
    "generic_password": r"(?i)password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}['\"]?",
}


def register_common_patterns() -> None:
    """Register common secret patterns for automatic detection.

    This registers patterns for AWS keys, GitHub tokens, Stripe keys, and more.
    Use this for defense-in-depth when you can't register individual secrets.

    Example:
        >>> from tripwire.security.logging import register_common_patterns
        >>> register_common_patterns()
        >>>
        >>> import logging
        >>> logging.info("AWS Key: AKIAIOSFODNN7EXAMPLE")
        >>> # Output: AWS Key: **********
    """
    for pattern_name, pattern_regex in COMMON_SECRET_PATTERNS.items():
        register_pattern(pattern_regex)


__all__ = [
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
