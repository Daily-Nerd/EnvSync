"""Core EnvSync functionality.

This module contains the main EnvSync class and the module-level singleton
instance used for environment variable management.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union

from dotenv import load_dotenv

from envsync.exceptions import (
    EnvFileNotFoundError,
    MissingVariableError,
    ValidationError,
)
from envsync.validation import (
    ValidatorFunc,
    coerce_type,
    get_validator,
    validate_choices,
    validate_pattern,
    validate_range,
)

T = TypeVar("T")


class EnvSync:
    """Main class for environment variable management with validation.

    This class provides methods to load, validate, and retrieve environment
    variables with type safety and format validation.
    """

    def __init__(
        self,
        env_file: Union[str, Path, None] = None,
        auto_load: bool = True,
        strict: bool = False,
        detect_secrets: bool = False,
    ) -> None:
        """Initialize EnvSync.

        Args:
            env_file: Path to .env file to load (default: .env)
            auto_load: Whether to automatically load .env file on init
            strict: Whether to enable strict mode (warnings become errors)
            detect_secrets: Whether to detect potential secrets
        """
        self.env_file = Path(env_file) if env_file else Path(".env")
        self.strict = strict
        self.detect_secrets = detect_secrets
        self._loaded_files: List[Path] = []
        self._registry: Dict[str, Dict[str, Any]] = {}

        if auto_load and self.env_file.exists():
            self.load(self.env_file)

    def load(self, env_file: Union[str, Path, None] = None, override: bool = False) -> None:
        """Load environment variables from .env file.

        Args:
            env_file: Path to .env file (default: use instance env_file)
            override: Whether to override existing environment variables

        Raises:
            EnvFileNotFoundError: If env file doesn't exist and is required
        """
        file_path = Path(env_file) if env_file else self.env_file

        if not file_path.exists():
            if self.strict:
                raise EnvFileNotFoundError(str(file_path))
            return

        load_dotenv(file_path, override=override)
        self._loaded_files.append(file_path)

    def load_files(self, file_paths: List[Union[str, Path]], override: bool = False) -> None:
        """Load multiple .env files in order.

        Args:
            file_paths: List of .env file paths to load
            override: Whether each file should override previous values
        """
        for file_path in file_paths:
            self.load(file_path, override=override)

    def require(
        self,
        name: str,
        *,
        type: type[T] = str,  # noqa: A002
        default: Optional[T] = None,
        description: Optional[str] = None,
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> T:
        """Get a required environment variable with validation.

        This method retrieves an environment variable and validates it according
        to the specified constraints. If validation fails, an exception is raised
        at import time, preventing the application from starting with invalid config.

        Args:
            name: Environment variable name
            type: Type to coerce to (default: str)
            default: Default value if not set (makes it optional)
            description: Human-readable description
            format: Built-in format validator (email, url, uuid, ipv4, postgresql)
            pattern: Custom regex pattern to validate against
            choices: List of allowed values
            min_val: Minimum value (for int/float)
            max_val: Maximum value (for int/float)
            validator: Custom validator function
            secret: Mark as secret (for secret detection)
            error_message: Custom error message

        Returns:
            Validated and type-coerced value

        Raises:
            MissingVariableError: If variable is missing and no default
            ValidationError: If variable fails validation
            TypeCoercionError: If type coercion fails
        """
        # Register variable for documentation generation
        self._register_variable(
            name=name,
            required=(default is None),
            type_=type,
            default=default,
            description=description,
            secret=secret,
        )

        # Get raw value from environment
        raw_value = os.getenv(name)

        # Handle missing value
        if raw_value is None:
            if default is not None:
                return default
            raise MissingVariableError(name, description)

        # Type coercion
        if type is not str:
            value = coerce_type(raw_value, type, name)
        else:
            value = raw_value  # type: ignore[assignment]

        # Format validation
        if format:
            validator_func = get_validator(format)
            if validator_func is None:
                raise ValidationError(
                    name,
                    raw_value,
                    error_message or f"Unknown format validator: {format}",
                    expected=format,
                )
            if not validator_func(raw_value):
                raise ValidationError(
                    name,
                    raw_value,
                    error_message or f"Invalid format: expected {format}",
                    expected=format,
                )

        # Pattern validation
        if pattern and not validate_pattern(raw_value, pattern):
            raise ValidationError(
                name,
                raw_value,
                error_message or f"Does not match pattern: {pattern}",
                expected=pattern,
            )

        # Choices validation
        if choices and not validate_choices(raw_value, choices):
            raise ValidationError(
                name,
                raw_value,
                error_message or f"Not in allowed choices: {choices}",
                expected=f"One of: {', '.join(choices)}",
            )

        # Range validation (for numeric types)
        if isinstance(value, (int, float)) and (min_val is not None or max_val is not None):
            if not validate_range(value, min_val, max_val):
                range_desc = []
                if min_val is not None:
                    range_desc.append(f">= {min_val}")
                if max_val is not None:
                    range_desc.append(f"<= {max_val}")
                raise ValidationError(
                    name,
                    value,
                    error_message or f"Out of range: must be {' and '.join(range_desc)}",
                    expected=" and ".join(range_desc),
                )

        # Custom validator
        if validator and not validator(value):
            raise ValidationError(
                name,
                value,
                error_message or "Failed custom validation",
            )

        return value

    def optional(
        self,
        name: str,
        *,
        default: T,
        type: type[T] = str,  # noqa: A002
        description: Optional[str] = None,
        format: Optional[str] = None,  # noqa: A002
        pattern: Optional[str] = None,
        choices: Optional[List[str]] = None,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
        validator: Optional[ValidatorFunc] = None,
        secret: bool = False,
        error_message: Optional[str] = None,
    ) -> T:
        """Get an optional environment variable with validation.

        This is a convenience wrapper around require() with a default value.

        Args:
            name: Environment variable name
            default: Default value if not set
            type: Type to coerce to (default: str)
            description: Human-readable description
            format: Built-in format validator
            pattern: Custom regex pattern
            choices: List of allowed values
            min_val: Minimum value (for int/float)
            max_val: Maximum value (for int/float)
            validator: Custom validator function
            secret: Mark as secret
            error_message: Custom error message

        Returns:
            Validated and type-coerced value or default
        """
        return self.require(
            name,
            type=type,
            default=default,
            description=description,
            format=format,
            pattern=pattern,
            choices=choices,
            min_val=min_val,
            max_val=max_val,
            validator=validator,
            secret=secret,
            error_message=error_message,
        )

    def get(
        self,
        name: str,
        default: Optional[T] = None,
        type: type[T] = str,  # noqa: A002
    ) -> Optional[T]:
        """Get an environment variable with optional type coercion.

        Simple getter without validation (for backwards compatibility).

        Args:
            name: Environment variable name
            default: Default value if not set
            type: Type to coerce to

        Returns:
            Value or default
        """
        raw_value = os.getenv(name)
        if raw_value is None:
            return default

        if type is str or type is None:
            return raw_value  # type: ignore[return-value]

        return coerce_type(raw_value, type, name)

    def has(self, name: str) -> bool:
        """Check if environment variable exists.

        Args:
            name: Environment variable name

        Returns:
            True if variable is set
        """
        return name in os.environ

    def all(self) -> Dict[str, str]:
        """Get all environment variables.

        Returns:
            Dictionary of all environment variables
        """
        return dict(os.environ)

    def _register_variable(
        self,
        name: str,
        required: bool,
        type_: type[Any],
        default: Any,
        description: Optional[str],
        secret: bool,
    ) -> None:
        """Register a variable for documentation generation.

        Args:
            name: Variable name
            required: Whether variable is required
            type_: Variable type
            default: Default value
            description: Description
            secret: Whether variable is secret
        """
        self._registry[name] = {
            "required": required,
            "type": type_.__name__,
            "default": default,
            "description": description,
            "secret": secret,
        }

    def get_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get the registry of all registered variables.

        Returns:
            Registry dictionary
        """
        return self._registry.copy()


# Module-level singleton instance for convenient usage
env = EnvSync()
