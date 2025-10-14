"""Plugin system exception hierarchy.

This module defines all exceptions that can be raised by the plugin system,
providing clear error messages and proper exception chaining.
"""

from __future__ import annotations


class SecurityWarning(UserWarning):
    """Warning for security-related configuration issues.

    Used to alert users about potentially insecure configurations that are
    allowed but not recommended, such as using HTTP instead of HTTPS for
    remote connections.
    """

    pass


class PluginError(Exception):
    """Base exception for all plugin-related errors.

    All plugin exceptions inherit from this class, allowing users to catch
    any plugin-related error with a single except clause.

    Example:
        >>> try:
        ...     registry.get_plugin("vault")
        ... except PluginError as e:
        ...     print(f"Plugin error: {e}")
    """

    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found.

    This occurs when:
    - Plugin is not registered in the PluginRegistry
    - Plugin entry point doesn't exist
    - Plugin module cannot be imported

    Attributes:
        plugin_name: Name of the plugin that was not found
    """

    def __init__(self, plugin_name: str, message: str | None = None) -> None:
        """Initialize PluginNotFoundError.

        Args:
            plugin_name: Name of the plugin that was not found
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        default_message = (
            f"Plugin '{plugin_name}' not found. " f"Ensure the plugin is installed and registered correctly."
        )
        super().__init__(message or default_message)


class PluginValidationError(PluginError):
    """Raised when plugin validation fails.

    This occurs when:
    - Plugin doesn't implement required protocol methods
    - Plugin metadata is invalid or missing
    - Plugin configuration is invalid
    - Plugin API version is incompatible

    Attributes:
        plugin_name: Name of the plugin that failed validation
        validation_errors: List of specific validation failures
    """

    def __init__(self, plugin_name: str, validation_errors: list[str], message: str | None = None) -> None:
        """Initialize PluginValidationError.

        Args:
            plugin_name: Name of the plugin that failed validation
            validation_errors: List of specific validation failures
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        self.validation_errors = validation_errors
        default_message = f"Plugin '{plugin_name}' failed validation:\n" + "\n".join(
            f"  - {error}" for error in validation_errors
        )
        super().__init__(message or default_message)


class PluginSecurityError(PluginError):
    """Raised when a plugin violates security constraints.

    This occurs when:
    - Plugin attempts to access restricted files
    - Plugin tries to make network requests to internal IPs
    - Plugin attempts to execute shell commands
    - Plugin tries to access Python internals (__dict__, __code__, etc.)

    Security violations are treated as critical errors and should prevent
    the plugin from being loaded or executed.

    Attributes:
        plugin_name: Name of the plugin that violated security
        violation_type: Type of security violation (e.g., "file_access", "network")
        details: Additional details about the violation
    """

    def __init__(self, plugin_name: str, violation_type: str, details: str, message: str | None = None) -> None:
        """Initialize PluginSecurityError.

        Args:
            plugin_name: Name of the plugin that violated security
            violation_type: Type of security violation
            details: Additional details about the violation
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        self.violation_type = violation_type
        self.details = details
        default_message = f"Security violation in plugin '{plugin_name}' ({violation_type}): {details}"
        super().__init__(message or default_message)


class PluginAPIError(PluginError):
    """Raised when a plugin encounters an API-related error.

    This occurs when:
    - Plugin's load() method raises an exception
    - Plugin's validate_config() method fails
    - Plugin returns invalid data types
    - Plugin method signature doesn't match protocol

    Attributes:
        plugin_name: Name of the plugin that encountered the error
        method_name: Name of the method that failed
        original_error: The original exception (if any)
    """

    def __init__(
        self,
        plugin_name: str,
        method_name: str,
        original_error: Exception | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize PluginAPIError.

        Args:
            plugin_name: Name of the plugin that encountered the error
            method_name: Name of the method that failed
            original_error: The original exception (if any)
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        self.method_name = method_name
        self.original_error = original_error

        if original_error:
            default_message = (
                f"Plugin '{plugin_name}' raised error in {method_name}(): "
                f"{type(original_error).__name__}: {original_error}"
            )
        else:
            default_message = f"Plugin '{plugin_name}' encountered API error in {method_name}()"

        super().__init__(message or default_message)


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load.

    This occurs when:
    - Plugin module import fails
    - Plugin entry point is invalid
    - Plugin initialization fails
    - Plugin dependencies are missing

    Attributes:
        plugin_name: Name of the plugin that failed to load
        reason: Reason for the load failure
        original_error: The original exception (if any)
    """

    def __init__(
        self,
        plugin_name: str,
        reason: str,
        original_error: Exception | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize PluginLoadError.

        Args:
            plugin_name: Name of the plugin that failed to load
            reason: Reason for the load failure
            original_error: The original exception (if any)
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        self.reason = reason
        self.original_error = original_error

        if original_error:
            default_message = (
                f"Failed to load plugin '{plugin_name}': {reason}. "
                f"Original error: {type(original_error).__name__}: {original_error}"
            )
        else:
            default_message = f"Failed to load plugin '{plugin_name}': {reason}"

        super().__init__(message or default_message)


class PluginVersionError(PluginError):
    """Raised when plugin version is incompatible with TripWire.

    This occurs when:
    - Plugin requires a newer TripWire version
    - Plugin is built for an older, incompatible TripWire API
    - Version constraints cannot be satisfied

    Attributes:
        plugin_name: Name of the plugin with version conflict
        plugin_version: Version of the plugin
        required_tripwire_version: TripWire version required by plugin
        current_tripwire_version: Current TripWire version
    """

    def __init__(
        self,
        plugin_name: str,
        plugin_version: str,
        required_tripwire_version: str,
        current_tripwire_version: str,
        message: str | None = None,
    ) -> None:
        """Initialize PluginVersionError.

        Args:
            plugin_name: Name of the plugin with version conflict
            plugin_version: Version of the plugin
            required_tripwire_version: TripWire version required by plugin
            current_tripwire_version: Current TripWire version
            message: Optional custom error message
        """
        self.plugin_name = plugin_name
        self.plugin_version = plugin_version
        self.required_tripwire_version = required_tripwire_version
        self.current_tripwire_version = current_tripwire_version

        default_message = (
            f"Plugin '{plugin_name}' v{plugin_version} requires TripWire >= {required_tripwire_version}, "
            f"but current version is {current_tripwire_version}"
        )
        super().__init__(message or default_message)
