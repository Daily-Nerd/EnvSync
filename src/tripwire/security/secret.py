"""Secret value wrapper for preventing accidental secret exposure.

This module provides a Secret[T] wrapper class that prevents secrets from being
accidentally leaked through print(), logging, error messages, or serialization.

Design Pattern:
    - Wrapper Pattern: Wraps sensitive values to control access
    - Explicit Interface: Requires get_secret_value() for intentional access
    - Type Safety: Generic type works with Python's type system

Security Features:
    - String masking in __str__() and __repr__()
    - JSON serialization protection
    - Logging integration (automatic redaction)
    - Equality comparison (constant-time to prevent timing attacks)
    - Hash support (for use in dicts/sets)

Example:
    >>> token: Secret[str] = Secret("my_secret_token")
    >>> print(token)
    **********
    >>> print(f"Token: {token}")
    Token: **********
    >>> actual_value = token.get_secret_value()  # Explicit access
    >>> print(actual_value)
    my_secret_token

Compatibility:
    - Compatible with Pydantic SecretStr (similar API)
    - Works with FastAPI, Django, Flask
    - Type checker support (mypy, pyright)
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any, Generic, Optional, TypeVar

# Generic type variable for Secret wrapper
T = TypeVar("T")

# Mask character used for display
MASK_STRING = "**********"


class Secret(Generic[T]):
    """Wrapper for secret values that prevents accidental exposure.

    This class wraps sensitive values (passwords, API keys, tokens) to prevent
    them from being accidentally logged, printed, or serialized. The actual value
    can only be accessed via the explicit get_secret_value() method.

    Design:
        - __str__() and __repr__() return masked strings
        - JSON serialization returns masked value (or raises error in strict mode)
        - Equality comparison uses constant-time comparison (timing attack resistant)
        - Hash is based on actual value (for dict/set usage)

    Type Safety:
        Secret[str] is a distinct type from str, preventing accidental usage.
        Type checkers will warn if you try to pass Secret[str] where str is expected.

    Thread Safety:
        This class is thread-safe (immutable after construction).

    Attributes:
        _value: The actual secret value (private)

    Example:
        >>> api_key: Secret[str] = Secret("sk-1234567890abcdef")
        >>> print(api_key)
        **********
        >>>
        >>> # Explicit access when needed
        >>> headers = {"Authorization": f"Bearer {api_key.get_secret_value()}"}
        >>>
        >>> # Safe logging
        >>> logger.info(f"API key configured: {api_key}")
        >>> # Output: API key configured: **********
    """

    __slots__ = ("_value",)  # Memory optimization + prevent attribute injection
    _value: T  # Explicit attribute declaration for mypy type checking

    def __init__(self, value: T) -> None:
        """Initialize the secret wrapper.

        Args:
            value: The secret value to wrap (string, token, password, etc.)

        Example:
            >>> token = Secret("my_secret_token")
            >>> api_key = Secret("sk-abc123")
        """
        # Store in a "private" attribute (name mangling provides some protection)
        object.__setattr__(self, "_value", value)

    def get_secret_value(self) -> T:
        """Get the actual secret value (use with caution).

        This is the ONLY way to access the actual secret value. This method
        should only be called when you explicitly need the secret (e.g., making
        API calls, database connections, etc.).

        Returns:
            The actual secret value

        Security Note:
            Be careful where you use the returned value. Once unwrapped, it's
            no longer protected and could be leaked through logs, errors, etc.

        Example:
            >>> token: Secret[str] = Secret("my_token")
            >>> vault = VaultClient(token=token.get_secret_value())
        """
        return self._value

    def __str__(self) -> str:
        """Return masked string representation.

        This prevents secrets from being leaked in print(), f-strings, str(),
        and string concatenation.

        Returns:
            Masked string (always "**********")

        Example:
            >>> token = Secret("my_secret_token")
            >>> print(token)
            **********
            >>> f"Token: {token}"
            'Token: **********'
        """
        return MASK_STRING

    def __repr__(self) -> str:
        """Return masked representation for debugging.

        This prevents secrets from being leaked in debuggers, error messages,
        and interactive shells.

        Returns:
            Masked representation like "Secret('**********')"

        Example:
            >>> token = Secret("my_secret_token")
            >>> repr(token)
            "Secret('**********')"
            >>> token  # In interactive shell
            Secret('**********')
        """
        return f"Secret('{MASK_STRING}')"

    def __eq__(self, other: object) -> bool:
        """Compare secrets using constant-time comparison.

        This prevents timing attacks where an attacker could guess a secret
        by measuring how long comparisons take.

        Args:
            other: Object to compare with (Secret or plain value)

        Returns:
            True if values are equal, False otherwise

        Security:
            Uses secrets.compare_digest() for constant-time comparison when
            comparing strings/bytes. For other types, falls back to standard
            equality (which may be vulnerable to timing attacks).

        Example:
            >>> secret1 = Secret("password123")
            >>> secret2 = Secret("password123")
            >>> secret3 = Secret("different")
            >>> secret1 == secret2
            True
            >>> secret1 == secret3
            False
            >>> secret1 == "password123"  # Also works with plain values
            True
        """
        # Get actual values for comparison
        if isinstance(other, Secret):
            other_value = other.get_secret_value()
        else:
            other_value = other

        # Use constant-time comparison for strings and bytes (timing attack protection)
        if isinstance(self._value, (str, bytes)) and isinstance(other_value, (str, bytes)):
            # Convert both to bytes for comparison
            self_bytes = self._value.encode() if isinstance(self._value, str) else self._value
            other_bytes = other_value.encode() if isinstance(other_value, str) else other_value

            return secrets.compare_digest(self_bytes, other_bytes)

        # For other types, use standard equality (no timing attack protection)
        return bool(self._value == other_value)

    def __hash__(self) -> int:
        """Return hash of the secret value.

        This allows Secret objects to be used as dictionary keys or in sets.
        The hash is based on the actual value, not the masked representation.

        Returns:
            Hash of the secret value

        Security Note:
            Hash collisions could potentially leak information about the secret.
            Avoid using secrets as dict keys in untrusted contexts.

        Example:
            >>> token1 = Secret("token_abc")
            >>> token2 = Secret("token_abc")
            >>> {token1: "value"}  # Can be used as dict key
            {Secret('**********'): 'value'}
            >>> token1 in {token2}  # Can be used in sets
            True
        """
        return hash(self._value)

    def __len__(self) -> int:
        """Return length of the secret value (if applicable).

        This allows len() to work on Secret wrappers when the underlying value
        supports it (strings, lists, etc.).

        Returns:
            Length of the secret value

        Security Note:
            Revealing the length could leak some information about the secret
            (e.g., "token is 32 characters long"). Use cautiously.

        Example:
            >>> token = Secret("my_secret_token")
            >>> len(token)
            15
        """
        # Only works if underlying value has __len__
        if hasattr(self._value, "__len__"):
            return len(self._value)
        else:
            raise TypeError(f"object of type '{type(self._value).__name__}' has no len()")

    def __bool__(self) -> bool:
        """Return truthiness of the secret value.

        This allows Secret wrappers to be used in boolean contexts (if statements, etc.).

        Returns:
            True if value is truthy, False otherwise

        Example:
            >>> token = Secret("my_token")
            >>> if token:
            ...     print("Token is set")
            Token is set
            >>>
            >>> empty = Secret("")
            >>> if not empty:
            ...     print("Token is empty")
            Token is empty
        """
        return bool(self._value)

    # Prevent attribute assignment (immutability)
    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent attribute modification (enforce immutability).

        Args:
            name: Attribute name
            value: Attribute value

        Raises:
            AttributeError: Always (Secret objects are immutable)
        """
        raise AttributeError("Secret objects are immutable")

    def __delattr__(self, name: str) -> None:
        """Prevent attribute deletion (enforce immutability).

        Args:
            name: Attribute name

        Raises:
            AttributeError: Always (Secret objects are immutable)
        """
        raise AttributeError("Secret objects are immutable")

    # Pickle serialization support (with immutability preservation)
    def __getstate__(self) -> dict[str, T]:
        """Support pickling while maintaining immutability.

        Returns:
            Dictionary containing the secret value for serialization

        Security Note:
            Pickled secrets can be stored/transmitted. Only pickle secrets
            in secure contexts (encrypted storage, trusted channels).
        """
        return {"_value": self._value}

    def __setstate__(self, state: dict[str, T]) -> None:
        """Restore Secret from pickle.

        Args:
            state: Dictionary containing the secret value

        Note:
            This bypasses immutability constraints to allow pickle deserialization.
            This is the only way to set _value after construction via pickle.
        """
        # Bypass immutability for pickle deserialization
        # Use object.__setattr__ to avoid our __setattr__ override
        object.__setattr__(self, "_value", state["_value"])

    # JSON serialization protection
    def __json__(self) -> str:
        """Custom JSON serialization (for libraries that support it).

        Returns:
            Masked string (not the actual secret)

        Example:
            >>> import json
            >>> token = Secret("my_token")
            >>> # Some JSON libraries call __json__() if available
            >>> token.__json__()
            '**********'
        """
        return MASK_STRING

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary (for serialization frameworks).

        Returns:
            Dictionary with masked value

        Example:
            >>> token = Secret("my_token")
            >>> token.to_dict()
            {'value': '**********', 'type': 'Secret'}
        """
        return {
            "value": MASK_STRING,
            "type": "Secret",
        }


class SecretStr(Secret[str]):
    """Convenience alias for Secret[str] (most common use case).

    This is API-compatible with Pydantic's SecretStr for easier migration.

    Example:
        >>> from tripwire.security.secret import SecretStr
        >>> api_key: SecretStr = SecretStr("sk-abc123")
        >>> print(api_key)
        **********
    """

    pass


class SecretBytes(Secret[bytes]):
    """Convenience alias for Secret[bytes] (for binary secrets).

    Example:
        >>> from tripwire.security.secret import SecretBytes
        >>> encryption_key: SecretBytes = SecretBytes(b"\\x00\\x01\\x02...")
        >>> print(encryption_key)
        **********
    """

    pass


# JSON encoder that handles Secret objects
class SecretJSONEncoder(json.JSONEncoder):
    """JSON encoder that masks Secret objects.

    This encoder can be used with json.dumps() to automatically mask secrets
    during serialization.

    Example:
        >>> import json
        >>> from tripwire.security.secret import Secret, SecretJSONEncoder
        >>>
        >>> data = {
        ...     "username": "admin",
        ...     "password": Secret("my_password"),
        ... }
        >>> json.dumps(data, cls=SecretJSONEncoder)
        '{"username": "admin", "password": "**********"}'
    """

    def default(self, obj: Any) -> Any:
        """Handle Secret objects during JSON encoding.

        Args:
            obj: Object to encode

        Returns:
            Masked string for Secret objects, default handling for others
        """
        if isinstance(obj, Secret):
            return MASK_STRING

        # Let the default encoder handle other types
        return super().default(obj)


# Strict JSON encoder that raises errors on Secret objects
class StrictSecretJSONEncoder(json.JSONEncoder):
    """JSON encoder that raises errors when encountering Secret objects.

    Use this in strict mode to prevent accidental serialization of secrets.

    Example:
        >>> import json
        >>> from tripwire.security.secret import Secret, StrictSecretJSONEncoder
        >>>
        >>> data = {"password": Secret("my_password")}
        >>> json.dumps(data, cls=StrictSecretJSONEncoder)
        Traceback (most recent call last):
            ...
        TypeError: Secret objects cannot be serialized to JSON. Use get_secret_value() explicitly if needed.
    """

    def default(self, obj: Any) -> Any:
        """Raise error when encountering Secret objects.

        Args:
            obj: Object to encode

        Raises:
            TypeError: If obj is a Secret
        """
        if isinstance(obj, Secret):
            raise TypeError(
                "Secret objects cannot be serialized to JSON. " "Use get_secret_value() explicitly if needed."
            )

        return super().default(obj)


def mask_secret_in_string(text: str, secret_value: str, mask: str = MASK_STRING) -> str:
    """Mask occurrences of a secret value in a string.

    This is useful for redacting secrets from log messages, error messages, etc.

    Args:
        text: Text that may contain the secret
        secret_value: The secret value to mask
        mask: The mask to replace with (default: "**********")

    Returns:
        Text with secret occurrences replaced by mask

    Security:
        Uses case-sensitive exact matching. Partial matches are not masked.

    Example:
        >>> text = "Error: Invalid token abc123 provided"
        >>> mask_secret_in_string(text, "abc123")
        'Error: Invalid token ********** provided'
    """
    if not secret_value:  # Don't mask empty strings
        return text

    return text.replace(secret_value, mask)


def mask_multiple_secrets(text: str, secrets: list[str], mask: str = MASK_STRING) -> str:
    """Mask multiple secret values in a string.

    Args:
        text: Text that may contain secrets
        secrets: List of secret values to mask
        mask: The mask to replace with (default: "**********")

    Returns:
        Text with all secret occurrences replaced by mask

    Example:
        >>> text = "User: admin, Password: pass123, API Key: key456"
        >>> mask_multiple_secrets(text, ["pass123", "key456"])
        'User: admin, Password: **********, API Key: **********'
    """
    result = text
    for secret_value in secrets:
        result = mask_secret_in_string(result, secret_value, mask)
    return result


# Type guard for Secret objects
def is_secret(obj: Any) -> bool:
    """Check if an object is a Secret wrapper.

    Args:
        obj: Object to check

    Returns:
        True if obj is a Secret, False otherwise

    Example:
        >>> from tripwire.security.secret import Secret, is_secret
        >>> token = Secret("my_token")
        >>> is_secret(token)
        True
        >>> is_secret("plain_string")
        False
    """
    return isinstance(obj, Secret)


# Unwrap helper for conditionally unwrapping secrets
def unwrap_secret(value: Secret[T] | T) -> T:
    """Unwrap a secret if it's a Secret object, otherwise return as-is.

    This is useful for functions that can accept either Secret or plain values.

    Args:
        value: Either a Secret wrapper or a plain value

    Returns:
        The unwrapped value

    Example:
        >>> from tripwire.security.secret import Secret, unwrap_secret
        >>> unwrap_secret(Secret("secret_value"))
        'secret_value'
        >>> unwrap_secret("plain_value")
        'plain_value'
    """
    if isinstance(value, Secret):
        return value.get_secret_value()
    return value


__all__ = [
    "Secret",
    "SecretStr",
    "SecretBytes",
    "SecretJSONEncoder",
    "StrictSecretJSONEncoder",
    "MASK_STRING",
    "mask_secret_in_string",
    "mask_multiple_secrets",
    "is_secret",
    "unwrap_secret",
]
