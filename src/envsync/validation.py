"""Validation functions and type coercion for environment variables.

This module provides built-in validators for common data types and formats,
as well as utilities for creating custom validators and a plugin system for
registering new format validators.
"""

import re
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from envsync.exceptions import TypeCoercionError

T = TypeVar("T")

# Type alias for validator functions
ValidatorFunc = Callable[[Any], bool]

# Global registry for custom format validators
_CUSTOM_VALIDATORS: Dict[str, ValidatorFunc] = {}


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
    """
    import json

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

    # Try quoted CSV with double quotes
    if '"' in value:
        items = []
        in_quotes = False
        current = []

        for char in value:
            if char == '"':
                in_quotes = not in_quotes
            elif char == delimiter and not in_quotes:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
            else:
                current.append(char)

        # Add last item
        item = "".join(current).strip()
        if item:
            items.append(item)

        if items:
            return items

    # Try quoted CSV with single quotes
    if "'" in value:
        items = []
        in_quotes = False
        current = []

        for char in value:
            if char == "'":
                in_quotes = not in_quotes
            elif char == delimiter and not in_quotes:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
            else:
                current.append(char)

        # Add last item
        item = "".join(current).strip()
        if item:
            items.append(item)

        if items:
            return items

    # Fall back to simple split
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
        ValueError: If value cannot be parsed
    """
    import json

    value = value.strip()

    # Try JSON parsing first
    if value.startswith("{") and value.endswith("}"):
        try:
            result = json.loads(value)
            if not isinstance(result, dict):
                raise ValueError("JSON must represent a dictionary")
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

    # Try key=value pairs
    result: Dict[str, Any] = {}
    pairs = []
    current = []
    in_quotes = False
    quote_char = None

    for char in value:
        if char in ('"', "'") and (quote_char is None or char == quote_char):
            in_quotes = not in_quotes
            quote_char = char if in_quotes else None
            current.append(char)
        elif char == "," and not in_quotes:
            pair = "".join(current).strip()
            if pair:
                pairs.append(pair)
            current = []
        else:
            current.append(char)

    # Add last pair
    pair = "".join(current).strip()
    if pair:
        pairs.append(pair)

    # Parse each key=value pair
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


def register_validator(name: str, validator_func: ValidatorFunc) -> None:
    """Register a custom format validator.

    This allows users to add their own format validators that can be used
    with the `format` parameter in `require()` and `optional()`.

    Args:
        name: Name of the validator format (e.g., "phone", "zip_code")
        validator_func: Function that takes a string value and returns bool

    Raises:
        ValueError: If validator name conflicts with built-in validator

    Example:
        >>> def validate_phone(value: str) -> bool:
        ...     return bool(re.match(r'^\\d{3}-\\d{3}-\\d{4}$', value))
        >>> register_validator("phone", validate_phone)
        >>> # Now can use format="phone" in require()
    """
    built_in_validators = {"email", "url", "uuid", "ipv4", "postgresql"}
    if name in built_in_validators:
        raise ValueError(
            f"Cannot register validator '{name}': conflicts with built-in validator. "
            f"Built-in validators: {', '.join(sorted(built_in_validators))}"
        )

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
    """Unregister a custom format validator.

    Args:
        name: Name of the validator to remove

    Returns:
        True if validator was removed, False if not found
    """
    if name in _CUSTOM_VALIDATORS:
        del _CUSTOM_VALIDATORS[name]
        return True
    return False


def get_validator(name: str) -> Optional[ValidatorFunc]:
    """Get a validator by name (built-in or custom).

    Args:
        name: Name of the validator

    Returns:
        Validator function or None if not found
    """
    # Check built-in validators first
    if name in _BUILTIN_VALIDATORS:
        return _BUILTIN_VALIDATORS[name]

    # Then check custom validators
    return _CUSTOM_VALIDATORS.get(name)


def list_validators() -> Dict[str, str]:
    """List all available validators (built-in and custom).

    Returns:
        Dictionary mapping validator names to their types ("built-in" or "custom")
    """
    result: Dict[str, str] = {}

    for name in _BUILTIN_VALIDATORS:
        result[name] = "built-in"

    for name in _CUSTOM_VALIDATORS:
        result[name] = "custom"

    return result


def clear_custom_validators() -> None:
    """Clear all custom validators.

    This is mainly useful for testing.
    """
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
    """Get all format validators (built-in and custom combined).

    Returns:
        Dictionary mapping validator names to validator functions
    """
    result = _BUILTIN_VALIDATORS.copy()
    result.update(_CUSTOM_VALIDATORS)
    return result
