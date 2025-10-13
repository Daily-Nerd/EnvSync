"""Validation functions and type coercion for environment variables.

This module provides built-in validators for common data types and formats,
as well as utilities for creating custom validators and a plugin system for
registering new format validators.

Thread Safety:
    All validator registry operations (register_validator, unregister_validator,
    get_validator, list_validators, clear_custom_validators) are thread-safe.
    They use a threading.Lock to ensure safe concurrent access in multi-threaded
    environments such as web servers, async workers, and parallel test runners.

    Example of thread-safe usage:
        >>> from concurrent.futures import ThreadPoolExecutor
        >>> def register_my_validator():
        ...     register_validator("my_format", lambda v: len(v) > 5)
        >>> with ThreadPoolExecutor(max_workers=10) as executor:
        ...     futures = [executor.submit(register_my_validator) for _ in range(10)]
"""

from __future__ import annotations

import re
import threading
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
    overload,
)

from tripwire.exceptions import TypeCoercionError

# TypeVar for generic type coercion - bound to supported types
# Note: Using List/Dict from typing for proper type-arg support
T = TypeVar("T", int, float, bool, str, List[Any], Dict[Any, Any])


# Protocol for validator functions - ensures proper typing
class ValidatorProtocol(Protocol):
    """Protocol for validator functions that take a value and return bool."""

    def __call__(self, value: Any) -> bool:
        """Validate a value.

        Args:
            value: Value to validate

        Returns:
            True if value is valid, False otherwise
        """
        ...


# Type alias for validator functions (backward compatibility)
ValidatorFunc = Callable[[Any], bool]

# Resource limits to prevent DOS attacks and memory exhaustion
MAX_LIST_STRING_LENGTH = 10_000  # 10KB max for list strings
MAX_DICT_STRING_LENGTH = 10_000  # 10KB max for dict strings
MAX_INT_STRING_LENGTH = 100  # Max 100 digits for integers
MAX_FLOAT_STRING_LENGTH = 100  # Max 100 digits for floats

# Global registry for custom format validators (thread-safe)
_CUSTOM_VALIDATORS: Dict[str, ValidatorFunc] = {}
_VALIDATOR_LOCK = threading.Lock()


def _parse_delimited_string(
    value: str,
    delimiter: str = ",",
    strip_quotes: bool = True,
) -> List[str]:
    """Parse a delimited string respecting quotes.

    Args:
        value: String to parse
        delimiter: Delimiter character (default: comma)
        strip_quotes: Whether to strip surrounding quotes

    Returns:
        List of parsed items
    """
    items = []
    current = []
    in_quotes = False
    quote_char = None

    for char in value:
        if char in ('"', "'") and (quote_char is None or char == quote_char):
            in_quotes = not in_quotes
            quote_char = char if in_quotes else None
            if not strip_quotes:
                current.append(char)
        elif char == delimiter and not in_quotes:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)

    # Add final item
    final = "".join(current).strip()
    if final:
        items.append(final)

    return items


def coerce_bool(value: str) -> bool:
    """Convert string to boolean.

    Handles common boolean representations:
    - True: "true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"
    - False: "false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF"

    Args:
        value: String value to convert

    Returns:
        Boolean value

    Raises:
        ValueError: If value cannot be interpreted as boolean
    """
    if value.lower() in ("true", "1", "yes", "on"):
        return True
    if value.lower() in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"Cannot interpret '{value}' as boolean")


def coerce_int(value: str) -> int:
    """Convert string to integer.

    Args:
        value: String value to convert

    Returns:
        Integer value

    Raises:
        ValueError: If value cannot be converted to int or exceeds length limit
    """
    # Security: Prevent integer overflow DOS by limiting string length
    if len(value) > MAX_INT_STRING_LENGTH:
        raise ValueError(
            f"Integer string too long: {len(value)} chars (max: {MAX_INT_STRING_LENGTH}). "
            "This may indicate a malicious input or configuration error."
        )
    return int(value)


def coerce_float(value: str) -> float:
    """Convert string to float.

    Args:
        value: String value to convert

    Returns:
        Float value

    Raises:
        ValueError: If value cannot be converted to float or exceeds length limit
    """
    # Security: Prevent float overflow DOS by limiting string length
    if len(value) > MAX_FLOAT_STRING_LENGTH:
        raise ValueError(
            f"Float string too long: {len(value)} chars (max: {MAX_FLOAT_STRING_LENGTH}). "
            "This may indicate a malicious input or configuration error."
        )
    return float(value)


def coerce_list(value: str, delimiter: str = ",") -> List[str]:
    """Convert delimited string to list with smart parsing.

    Supports multiple formats:
    1. JSON arrays: '["item1", "item2"]'
    2. Quoted CSV: '"item1", "item2"' or "'item1', 'item2'"
    3. Simple CSV: 'item1, item2, item3'

    Args:
        value: String value to convert
        delimiter: Delimiter character (default: comma)

    Returns:
        List of strings

    Raises:
        ValueError: If value exceeds maximum length
    """
    import json

    # Security: Prevent memory exhaustion by limiting list string length
    if len(value) > MAX_LIST_STRING_LENGTH:
        raise ValueError(
            f"List string too large: {len(value)} chars (max: {MAX_LIST_STRING_LENGTH}). "
            "This may indicate a malicious input or configuration error."
        )

    value = value.strip()

    # Try JSON parsing first
    if value.startswith("[") and value.endswith("]"):
        try:
            result = json.loads(value)
            if isinstance(result, list):
                # Convert all items to strings for consistency
                return [str(item) for item in result]
        except json.JSONDecodeError:
            pass

    # Use common parsing utility for quoted or unquoted CSV
    if '"' in value or "'" in value:
        return _parse_delimited_string(value, delimiter, strip_quotes=True)

    # Fall back to simple split for unquoted values
    return [item.strip() for item in value.split(delimiter) if item.strip()]


def coerce_dict(value: str) -> Dict[str, Any]:
    """Convert string to dictionary with smart parsing.

    Supports multiple formats:
    1. JSON objects: '{"key": "value"}'
    2. Key=value pairs: 'key1=value1,key2=value2'
    3. Quoted key=value: 'key1="value 1",key2="value 2"'

    Args:
        value: String to convert

    Returns:
        Dictionary

    Raises:
        ValueError: If value cannot be parsed or exceeds length limit
    """
    import json

    # Security: Prevent memory exhaustion by limiting dict string length
    if len(value) > MAX_DICT_STRING_LENGTH:
        raise ValueError(
            f"Dict string too large: {len(value)} chars (max: {MAX_DICT_STRING_LENGTH}). "
            "This may indicate a malicious input or configuration error."
        )

    value = value.strip()

    # Try JSON parsing first
    if value.startswith("{") and value.endswith("}"):
        try:
            json_result = json.loads(value)
            if not isinstance(json_result, dict):
                raise ValueError("JSON must represent a dictionary")
            return json_result
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    # Use common parsing utility to split key=value pairs
    pairs = _parse_delimited_string(value, delimiter=",", strip_quotes=False)

    # Parse each key=value pair
    result: Dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid key=value pair: {pair}")

        key, _, val = pair.partition("=")
        key = key.strip()
        val = val.strip()

        # Remove quotes from value if present
        if len(val) >= 2:
            if (val[0] == '"' and val[-1] == '"') or (val[0] == "'" and val[-1] == "'"):
                val = val[1:-1]

        # Try to parse value as JSON primitive
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass  # Keep as string

        result[key] = val

    if not result:
        raise ValueError("No valid key=value pairs found")

    return result


def coerce_type(value: str, target_type: type[T], variable_name: str) -> T:
    """Coerce string value to target type.

    This function uses TypeVar to ensure return type matches the input type parameter.
    The TypeVar T is bound to (int, float, bool, str, list, dict) for type safety.

    Args:
        value: String value to coerce
        target_type: Type to coerce to (must be one of: int, float, bool, str, list, dict)
        variable_name: Name of the variable (for error messages)

    Returns:
        Value coerced to target type, with proper type inference

    Raises:
        TypeCoercionError: If coercion fails

    Example:
        >>> result: int = coerce_type("42", int, "PORT")
        >>> result  # Type checker knows this is int
        42
    """
    try:
        # Type checking: mypy now correctly infers types from runtime checks
        if target_type is bool:
            return coerce_bool(value)  # type: ignore[return-value]
        elif target_type is int:
            return coerce_int(value)  # type: ignore[return-value]
        elif target_type is float:
            return coerce_float(value)  # type: ignore[return-value]
        elif target_type is list:
            return coerce_list(value)  # type: ignore[return-value]
        elif target_type is dict:
            return coerce_dict(value)  # type: ignore[return-value]
        elif target_type is str:
            return value  # type: ignore[return-value]
        else:
            # Try direct type conversion for custom types
            return target_type(value)  # type: ignore[arg-type]
    except (ValueError, TypeError) as e:
        raise TypeCoercionError(variable_name, value, target_type, e) from e


def validate_email(value: str) -> bool:
    """Validate email address format.

    Args:
        value: Email address to validate

    Returns:
        True if valid email format
    """
    # Fixed ReDoS: Added upper bounds to all quantifiers
    # Local part: max 64 chars (RFC 5321), domain: max 255 chars, TLD: max 24 chars
    pattern = r"^[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,255}\.[a-zA-Z]{2,24}$"
    return bool(re.match(pattern, value))


def validate_url(value: str) -> bool:
    """Validate URL format.

    Args:
        value: URL to validate

    Returns:
        True if valid URL format
    """
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, value))


def validate_uuid(value: str) -> bool:
    """Validate UUID format.

    Args:
        value: UUID to validate

    Returns:
        True if valid UUID format
    """
    pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(pattern, value, re.IGNORECASE))


def validate_ipv4(value: str) -> bool:
    """Validate IPv4 address format.

    Args:
        value: IP address to validate

    Returns:
        True if valid IPv4 format
    """
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, value):
        return False

    # Check each octet is in valid range (0-255)
    octets = [int(x) for x in value.split(".")]
    return all(0 <= octet <= 255 for octet in octets)


def validate_postgresql_url(value: str) -> bool:
    """Validate PostgreSQL connection URL format.

    Args:
        value: Database URL to validate

    Returns:
        True if valid PostgreSQL URL format
    """
    pattern = r"^postgres(ql)?://.*"
    return bool(re.match(pattern, value))


def validate_pattern(value: str, pattern: str) -> bool:
    """Validate value against custom regex pattern.

    Args:
        value: Value to validate
        pattern: Regex pattern

    Returns:
        True if value matches pattern
    """
    return bool(re.match(pattern, value))


def validate_range(
    value: Union[int, float],
    min_val: Optional[Union[int, float]],
    max_val: Optional[Union[int, float]],
) -> bool:
    """Validate that value is within specified range.

    Args:
        value: Value to validate
        min_val: Minimum value (inclusive), or None for no minimum
        max_val: Maximum value (inclusive), or None for no maximum

    Returns:
        True if value is within range
    """
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value > max_val:
        return False
    return True


def validate_choices(value: str, choices: List[str]) -> bool:
    """Validate that value is one of allowed choices.

    Args:
        value: Value to validate
        choices: List of allowed values

    Returns:
        True if value is in choices
    """
    return value in choices


def validate_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> bool:
    """Validate string length is within bounds.

    Args:
        value: String value to validate
        min_length: Minimum length (inclusive), or None for no minimum
        max_length: Maximum length (inclusive), or None for no maximum

    Returns:
        True if string length is within bounds
    """
    length = len(value)
    if min_length is not None and length < min_length:
        return False
    if max_length is not None and length > max_length:
        return False
    return True


def validate_url_components(
    value: str,
    protocols: Optional[List[str]] = None,
    allowed_ports: Optional[List[int]] = None,
    forbidden_ports: Optional[List[int]] = None,
    required_path: Optional[str] = None,
    required_params: Optional[List[str]] = None,
    forbidden_params: Optional[List[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Validate URL components against specific requirements.

    This validator provides fine-grained control over URL structure beyond
    basic format validation. Use it to enforce security policies and API
    requirements.

    Args:
        value: URL string to validate
        protocols: Whitelist of allowed protocols (schemes).
            Example: ["https", "wss"] to only allow secure protocols
        allowed_ports: Whitelist of allowed port numbers.
            Example: [443, 8443] to only allow specific HTTPS ports
        forbidden_ports: Blacklist of forbidden port numbers.
            Example: [22, 3389] to prevent SSH/RDP in API URLs
        required_path: Regex pattern that path must match.
            Example: "^/api/v[0-9]+" to require versioned API paths
        required_params: List of query parameters that must be present.
            Example: ["api_key", "version"] to require authentication
        forbidden_params: List of query parameters that must not be present.
            Example: ["debug", "test"] to prevent debug flags in production

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
        If invalid, error_message explains which component failed.

    Example:
        >>> # Enforce HTTPS-only with specific ports
        >>> valid, error = validate_url_components(
        ...     "https://api.example.com:443/v1/users?api_key=xxx",
        ...     protocols=["https"],
        ...     allowed_ports=[443, 8443],
        ...     required_path="^/v[0-9]+/",
        ...     required_params=["api_key"],
        ...     forbidden_params=["debug"]
        ... )
        >>> valid
        True

        >>> # Detect invalid protocol
        >>> valid, error = validate_url_components(
        ...     "http://api.example.com",
        ...     protocols=["https"]
        ... )
        >>> valid
        False
        >>> error
        "Protocol 'http' not allowed. Allowed protocols: https"
    """
    from urllib.parse import parse_qs, urlparse

    try:
        parsed = urlparse(value)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    # Validate protocol (scheme)
    if protocols is not None:
        if not parsed.scheme:
            return False, "URL missing protocol/scheme"
        if parsed.scheme not in protocols:
            allowed = ", ".join(protocols)
            return False, f"Protocol '{parsed.scheme}' not allowed. Allowed protocols: {allowed}"

    # Validate port
    port = parsed.port
    if port is not None:
        # Check forbidden ports (blacklist)
        if forbidden_ports is not None and port in forbidden_ports:
            return False, f"Port {port} is forbidden"

        # Check allowed ports (whitelist)
        if allowed_ports is not None and port not in allowed_ports:
            allowed = ", ".join(str(p) for p in sorted(allowed_ports))
            return False, f"Port {port} not allowed. Allowed ports: {allowed}"

    # Validate path
    if required_path is not None:
        if not parsed.path:
            return False, f"URL path missing. Required pattern: {required_path}"
        if not re.match(required_path, parsed.path):
            return False, f"URL path '{parsed.path}' does not match required pattern: {required_path}"

    # Validate query parameters
    if required_params is not None or forbidden_params is not None:
        query_params = parse_qs(parsed.query)
        param_names = set(query_params.keys())

        # Check required parameters
        if required_params is not None:
            missing = [p for p in required_params if p not in param_names]
            if missing:
                return False, f"Missing required query parameters: {', '.join(missing)}"

        # Check forbidden parameters
        if forbidden_params is not None:
            present = [p for p in forbidden_params if p in param_names]
            if present:
                return False, f"Forbidden query parameters present: {', '.join(present)}"

    return True, None


def validate_datetime(
    value: str,
    formats: Optional[List[str]] = None,
    require_timezone: Optional[bool] = None,
    min_datetime: Optional[str] = None,
    max_datetime: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Validate datetime string against format and range requirements.

    This validator provides flexible datetime validation for timestamps,
    scheduled tasks, and time-sensitive configurations.

    Args:
        value: Datetime string to validate
        formats: List of accepted formats. Use "ISO8601" for ISO 8601 format,
            or provide strptime format strings (e.g., "%Y-%m-%d %H:%M:%S").
            Default: ["ISO8601"]
        require_timezone: If True, datetime must be timezone-aware.
            If False, datetime must be timezone-naive. If None, both allowed.
        min_datetime: Minimum allowed datetime (ISO 8601 format).
            Example: "2020-01-01T00:00:00Z"
        max_datetime: Maximum allowed datetime (ISO 8601 format).
            Example: "2030-12-31T23:59:59Z"

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
        If invalid, error_message explains which check failed.

    Example:
        >>> # Validate ISO 8601 with timezone
        >>> valid, error = validate_datetime(
        ...     "2025-10-13T14:30:00Z",
        ...     formats=["ISO8601"],
        ...     require_timezone=True
        ... )
        >>> valid
        True

        >>> # Validate custom format without timezone
        >>> valid, error = validate_datetime(
        ...     "2025-10-13 14:30:00",
        ...     formats=["%Y-%m-%d %H:%M:%S"],
        ...     require_timezone=False
        ... )
        >>> valid
        True

        >>> # Validate date range
        >>> valid, error = validate_datetime(
        ...     "2025-10-13T14:30:00Z",
        ...     min_datetime="2020-01-01T00:00:00Z",
        ...     max_datetime="2030-12-31T23:59:59Z"
        ... )
        >>> valid
        True
    """
    from datetime import datetime, timezone

    # Default to ISO8601 format if not specified
    if formats is None:
        formats = ["ISO8601"]

    # Try to parse datetime using provided formats
    parsed_dt = None
    for fmt in formats:
        try:
            if fmt == "ISO8601":
                # Use fromisoformat for ISO 8601 parsing (Python 3.7+)
                # Handle 'Z' suffix (UTC timezone indicator)
                value_normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
                parsed_dt = datetime.fromisoformat(value_normalized)
            else:
                # Use strptime for custom formats
                parsed_dt = datetime.strptime(value, fmt)
            break  # Successfully parsed
        except (ValueError, AttributeError):
            continue  # Try next format

    if parsed_dt is None:
        formats_str = ", ".join(formats)
        return False, f"Datetime '{value}' does not match any accepted format: {formats_str}"

    # Validate timezone requirement
    if require_timezone is not None:
        is_aware = parsed_dt.tzinfo is not None and parsed_dt.tzinfo.utcoffset(None) is not None

        if require_timezone and not is_aware:
            return False, f"Datetime '{value}' must include timezone information"

        if not require_timezone and is_aware:
            return False, f"Datetime '{value}' must not include timezone information"

    # Validate min_datetime
    if min_datetime is not None:
        try:
            min_dt_normalized = min_datetime.replace("Z", "+00:00") if min_datetime.endswith("Z") else min_datetime
            min_dt = datetime.fromisoformat(min_dt_normalized)

            # Compare dates (handle timezone-aware vs naive)
            if parsed_dt.tzinfo is None and min_dt.tzinfo is not None:
                # Make min_dt naive for comparison
                min_dt = min_dt.replace(tzinfo=None)
            elif parsed_dt.tzinfo is not None and min_dt.tzinfo is None:
                # Make min_dt aware for comparison (assume UTC)
                min_dt = min_dt.replace(tzinfo=timezone.utc)

            if parsed_dt < min_dt:
                return False, f"Datetime '{value}' is before minimum allowed: {min_datetime}"
        except (ValueError, AttributeError) as e:
            return False, f"Invalid min_datetime format '{min_datetime}': {e}"

    # Validate max_datetime
    if max_datetime is not None:
        try:
            max_dt_normalized = max_datetime.replace("Z", "+00:00") if max_datetime.endswith("Z") else max_datetime
            max_dt = datetime.fromisoformat(max_dt_normalized)

            # Compare dates (handle timezone-aware vs naive)
            if parsed_dt.tzinfo is None and max_dt.tzinfo is not None:
                # Make max_dt naive for comparison
                max_dt = max_dt.replace(tzinfo=None)
            elif parsed_dt.tzinfo is not None and max_dt.tzinfo is None:
                # Make max_dt aware for comparison (assume UTC)
                max_dt = max_dt.replace(tzinfo=timezone.utc)

            if parsed_dt > max_dt:
                return False, f"Datetime '{value}' is after maximum allowed: {max_datetime}"
        except (ValueError, AttributeError) as e:
            return False, f"Invalid max_datetime format '{max_datetime}': {e}"

    return True, None


def validator(func: ValidatorFunc) -> ValidatorFunc:
    """Decorator for creating custom validator functions.

    Args:
        func: Function that takes a value and returns bool

    Returns:
        Decorated validator function

    Example:
        >>> @validator
        ... def my_validator(value: Any) -> bool:
        ...     return len(str(value)) > 5
    """
    return func


def register_validator(name: str, validator_func: ValidatorFunc) -> None:
    """Register a custom format validator (thread-safe).

    This allows users to add their own format validators that can be used
    with the `format` parameter in `require()` and `optional()`.

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Args:
        name: Name of the validator format (e.g., "phone", "zip_code")
        validator_func: Function that takes a string value and returns bool.
            Should match ValidatorFunc type: Callable[[Any], bool]

    Raises:
        ValueError: If validator name conflicts with built-in validator

    Example:
        >>> def validate_phone(value: str) -> bool:
        ...     return bool(re.match(r'^\\d{3}-\\d{3}-\\d{4}$', value))
        >>> register_validator("phone", validate_phone)
        >>> # Now can use format="phone" in require()
    """
    built_in_validators = set(_BUILTIN_VALIDATORS.keys())
    if name in built_in_validators:
        raise ValueError(
            f"Cannot register validator '{name}': conflicts with built-in validator. "
            f"Built-in validators: {', '.join(sorted(built_in_validators))}"
        )

    with _VALIDATOR_LOCK:
        _CUSTOM_VALIDATORS[name] = validator_func


def register_validator_decorator(name: str) -> Callable[[ValidatorFunc], ValidatorFunc]:
    """Decorator for registering custom format validators.

    This is a convenience decorator that combines function definition and registration.

    Args:
        name: Name of the validator format

    Returns:
        Decorator function

    Example:
        >>> @register_validator_decorator("phone")
        ... def validate_phone(value: str) -> bool:
        ...     return bool(re.match(r'^\\d{3}-\\d{3}-\\d{4}$', value))
    """

    def decorator(func: ValidatorFunc) -> ValidatorFunc:
        register_validator(name, func)
        return func

    return decorator


def unregister_validator(name: str) -> bool:
    """Unregister a custom format validator (thread-safe).

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Args:
        name: Name of the validator to remove

    Returns:
        True if validator was removed, False if not found
    """
    with _VALIDATOR_LOCK:
        if name in _CUSTOM_VALIDATORS:
            del _CUSTOM_VALIDATORS[name]
            return True
        return False


def get_validator(name: str) -> Optional[ValidatorFunc]:
    """Get a validator by name (built-in or custom, thread-safe).

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Args:
        name: Name of the validator

    Returns:
        Validator function or None if not found
    """
    # Check built-in validators first (immutable, no lock needed)
    if name in _BUILTIN_VALIDATORS:
        return _BUILTIN_VALIDATORS[name]

    # Then check custom validators (thread-safe access)
    with _VALIDATOR_LOCK:
        return _CUSTOM_VALIDATORS.get(name)


def list_validators() -> Dict[str, str]:
    """List all available validators (built-in and custom, thread-safe).

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Returns:
        Dictionary mapping validator names to their types ("built-in" or "custom")
    """
    result: Dict[str, str] = {}

    # Built-in validators are immutable, no lock needed
    for name in _BUILTIN_VALIDATORS:
        result[name] = "built-in"

    # Custom validators require thread-safe access
    with _VALIDATOR_LOCK:
        for name in _CUSTOM_VALIDATORS:
            result[name] = "custom"

    return result


def clear_custom_validators() -> None:
    """Clear all custom validators (thread-safe).

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Note:
        This is mainly useful for testing and cleanup scenarios.
    """
    with _VALIDATOR_LOCK:
        _CUSTOM_VALIDATORS.clear()


# Built-in format validators
_BUILTIN_VALIDATORS: Dict[str, ValidatorFunc] = {
    "email": validate_email,
    "url": validate_url,
    "uuid": validate_uuid,
    "ipv4": validate_ipv4,
    "postgresql": validate_postgresql_url,
}


# Format validators mapping (includes both built-in and custom)
# This is used by core.py for backward compatibility
FORMAT_VALIDATORS: Dict[str, ValidatorFunc] = _BUILTIN_VALIDATORS.copy()


def get_all_format_validators() -> Dict[str, ValidatorFunc]:
    """Get all format validators (built-in and custom combined, thread-safe).

    Thread Safety:
        This function is thread-safe and can be called concurrently from
        multiple threads without risk of race conditions.

    Returns:
        Dictionary mapping validator names to validator functions
    """
    result = _BUILTIN_VALIDATORS.copy()
    with _VALIDATOR_LOCK:
        result.update(_CUSTOM_VALIDATORS)
    return result
