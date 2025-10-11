"""Thread-safe variable registry for TripWire.

This module provides a thread-safe registry for storing metadata about
environment variables declared in the application. It's used for:
- Documentation generation (.env.example files)
- Schema generation (.tripwire.toml files)
- Variable introspection and validation
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class VariableMetadata:
    """Metadata for a registered environment variable.

    Attributes:
        name: Variable name (e.g., "DATABASE_URL")
        required: Whether the variable is required (no default provided)
        type_name: String representation of the type (e.g., "str", "int")
        default: Default value if provided, None otherwise
        description: Human-readable description for documentation
        secret: Whether the variable contains sensitive data
    """

    name: str
    required: bool
    type_name: str
    default: Any = None
    description: Optional[str] = None
    secret: bool = False


class VariableRegistry:
    """Thread-safe registry for environment variable metadata.

    This class implements a thread-safe registry using a lock to prevent
    race conditions when multiple threads register variables simultaneously.
    Common in web servers (Flask/Django) and async applications.

    Thread Safety:
        All operations (register, get, get_all, clear) are protected by a lock
        to ensure atomicity and prevent race conditions.

    Design Pattern:
        - Singleton-like usage via TripWire instance
        - Thread-safe dictionary wrapper with lock protection
        - Immutable snapshots via get_all() to prevent external mutation

    Example:
        >>> registry = VariableRegistry()
        >>> metadata = VariableMetadata(
        ...     name="DATABASE_URL",
        ...     required=True,
        ...     type_name="str",
        ...     secret=True
        ... )
        >>> registry.register(metadata)
        >>> var = registry.get("DATABASE_URL")
        >>> assert var.secret is True
    """

    def __init__(self) -> None:
        """Initialize an empty registry with thread-safe lock."""
        self._lock = threading.Lock()
        self._variables: Dict[str, VariableMetadata] = {}

    def register(self, metadata: VariableMetadata) -> None:
        """Register a variable with its metadata.

        If a variable with the same name already exists, it will be overwritten
        with the new metadata. This is the expected behavior when a variable
        is declared multiple times (last declaration wins).

        Args:
            metadata: Variable metadata to register

        Thread Safety:
            Uses lock to ensure atomic registration, preventing race conditions
            where two threads register the same variable simultaneously.
        """
        with self._lock:
            self._variables[metadata.name] = metadata

    def get(self, name: str) -> Optional[VariableMetadata]:
        """Retrieve metadata for a variable by name.

        Args:
            name: Variable name to lookup

        Returns:
            VariableMetadata if found, None otherwise

        Thread Safety:
            Uses lock to ensure consistent read, preventing TOCTOU issues
            where a variable could be deleted between check and use.
        """
        with self._lock:
            return self._variables.get(name)

    def get_all(self) -> Dict[str, VariableMetadata]:
        """Get a snapshot of all registered variables.

        Returns:
            Dictionary mapping variable names to their metadata.
            This is a shallow copy to prevent external mutation of the registry.

        Thread Safety:
            Uses lock to ensure atomic snapshot, preventing inconsistent state
            where some variables are from before a concurrent modification
            and others are from after.
        """
        with self._lock:
            # Shallow copy prevents external mutation of registry
            return self._variables.copy()

    def clear(self) -> None:
        """Clear all registered variables.

        This is primarily used for testing to reset state between test cases.

        Thread Safety:
            Uses lock to ensure atomic clear operation.
        """
        with self._lock:
            self._variables.clear()
