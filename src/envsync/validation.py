"""Validation functions and type coercion for environment variables.

This module provides built-in validators for common data types and formats,
as well as utilities for creating custom validators.
"""

import re
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from envsync.exceptions import TypeCoercionError

T = TypeVar("T")

# Type alias for validator functions
ValidatorFunc = Callable[[Any], bool]


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
        ValueError: If value cannot be converted to int
    """
    return int(value)


def coerce_float(value: str) -> float:
    """Convert string to float.

    Args:
        value: String value to convert

    Returns:
        Float value

    Raises:
        ValueError: If value cannot be converted to float
    """
    return float(value)


def coerce_list(value: str, delimiter: str = ",") -> List[str]:
    """Convert delimited string to list.

    Args:
        value: String value to convert
        delimiter: Delimiter character (default: comma)

    Returns:
        List of strings
    """
    return [item.strip() for item in value.split(delimiter) if item.strip()]


def coerce_dict(value: str) -> Dict[str, Any]:
    """Convert JSON string to dictionary.

    Args:
        value: JSON string to convert

    Returns:
        Dictionary

    Raises:
        ValueError: If value is not valid JSON
    """
    import json

    try:
        result = json.loads(value)
        if not isinstance(result, dict):
            raise ValueError("JSON must represent a dictionary")
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def coerce_type(value: str, target_type: type[T], variable_name: str) -> T:
    """Coerce string value to target type.

    Args:
        value: String value to coerce
        target_type: Type to coerce to
        variable_name: Name of the variable (for error messages)

    Returns:
        Value coerced to target type

    Raises:
        TypeCoercionError: If coercion fails
    """
    try:
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
            # Try direct type conversion
            return target_type(value)  # type: ignore[return-value]
    except (ValueError, TypeError) as e:
        raise TypeCoercionError(variable_name, value, target_type, e) from e


def validate_email(value: str) -> bool:
    """Validate email address format.

    Args:
        value: Email address to validate

    Returns:
        True if valid email format
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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


def validator(func: ValidatorFunc) -> ValidatorFunc:
    """Decorator for creating custom validator functions.

    Args:
        func: Function that takes a value and returns bool

    Returns:
        Decorated validator function
    """
    return func


# Format validators mapping
FORMAT_VALIDATORS: Dict[str, ValidatorFunc] = {
    "email": validate_email,
    "url": validate_url,
    "uuid": validate_uuid,
    "ipv4": validate_ipv4,
    "postgresql": validate_postgresql_url,
}
