"""Validation orchestration using Chain of Responsibility pattern.

This module provides a composable validation system that extracts validation
logic from the TripWire.require() method into reusable validation rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, List, Optional


@dataclass
class ValidationContext:
    """Context passed through validation chain.

    Attributes:
        name: Name of the environment variable
        raw_value: Original string value from environment
        coerced_value: Value after type coercion
        expected_type: The type the value should be
    """

    name: str
    raw_value: str
    coerced_value: Any
    expected_type: type


class ValidationRule(ABC):
    """Abstract base class for validation rules.

    Each rule represents a single validation concern (format, range, pattern, etc.)
    and can be composed into validation chains using the ValidationOrchestrator.
    """

    def __init__(self, error_message: Optional[str] = None):
        """Initialize rule with optional custom error message.

        Args:
            error_message: Custom error message to use instead of default
        """
        self.error_message = error_message

    @abstractmethod
    def validate(self, context: ValidationContext) -> None:
        """Validate value in context.

        Args:
            context: Validation context with value and metadata

        Raises:
            ValidationError: If validation fails
        """
        pass

    def _format_error(self, default_message: str, context: ValidationContext) -> str:
        """Format error message with context.

        Args:
            default_message: Default error message to use
            context: Validation context for variable name

        Returns:
            Formatted error message
        """
        if self.error_message:
            return self.error_message
        return f"{context.name}: {default_message}"


class FormatValidationRule(ValidationRule):
    """Validates using format validators (email, url, postgresql, etc.).

    Uses the existing validator system from tripwire.validation.
    """

    def __init__(self, format_name: str, error_message: Optional[str] = None):
        """Initialize format validation rule.

        Args:
            format_name: Name of format validator to use
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.format_name = format_name

    def validate(self, context: ValidationContext) -> None:
        """Validate value matches format."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import get_validator

        validator = get_validator(self.format_name)
        if validator is None:
            raise ValidationError(
                variable_name=context.name,
                value=context.raw_value,
                reason=f"Unknown format validator '{self.format_name}'",
            )

        if not validator(context.raw_value):
            reason = self.error_message if self.error_message else f"Invalid format: expected {self.format_name}"
            raise ValidationError(variable_name=context.name, value=context.raw_value, reason=reason)


class PatternValidationRule(ValidationRule):
    """Validates using regex pattern."""

    def __init__(self, pattern: str, error_message: Optional[str] = None):
        """Initialize pattern validation rule.

        Args:
            pattern: Regular expression pattern
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.pattern = pattern

    def validate(self, context: ValidationContext) -> None:
        """Validate value matches pattern."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_pattern

        if not validate_pattern(context.raw_value, self.pattern):
            reason = self.error_message if self.error_message else f"Value does not match pattern: {self.pattern}"
            raise ValidationError(variable_name=context.name, value=context.raw_value, reason=reason)


class ChoicesValidationRule(ValidationRule):
    """Validates value is in allowed choices."""

    def __init__(self, choices: List[str], error_message: Optional[str] = None):
        """Initialize choices validation rule.

        Args:
            choices: List of allowed string values
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.choices = choices

    def validate(self, context: ValidationContext) -> None:
        """Validate value is in allowed choices."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_choices

        if not validate_choices(context.raw_value, self.choices):
            reason = self.error_message if self.error_message else f"Value must be one of: {', '.join(self.choices)}"
            raise ValidationError(variable_name=context.name, value=context.raw_value, reason=reason)


class RangeValidationRule(ValidationRule):
    """Validates numeric value is within range."""

    def __init__(
        self,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        """Initialize range validation rule.

        Args:
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, context: ValidationContext) -> None:
        """Validate numeric value is within range."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_range

        # Only validate if coerced value is numeric
        if not isinstance(context.coerced_value, (int, float)):
            return

        if not validate_range(context.coerced_value, self.min_val, self.max_val):
            range_desc = []
            if self.min_val is not None:
                range_desc.append(f"min={self.min_val}")
            if self.max_val is not None:
                range_desc.append(f"max={self.max_val}")

            reason = self.error_message if self.error_message else f"Value out of range ({', '.join(range_desc)})"
            raise ValidationError(variable_name=context.name, value=context.coerced_value, reason=reason)


class LengthValidationRule(ValidationRule):
    """Validates string length is within bounds."""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Initialize length validation rule.

        Args:
            min_length: Minimum string length
            max_length: Maximum string length
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, context: ValidationContext) -> None:
        """Validate string length is within bounds."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_length

        # Only validate if coerced value is string
        if not isinstance(context.coerced_value, str):
            return

        if not validate_length(context.coerced_value, self.min_length, self.max_length):
            length_desc = []
            if self.min_length is not None:
                length_desc.append(f"min_length={self.min_length}")
            if self.max_length is not None:
                length_desc.append(f"max_length={self.max_length}")

            reason = (
                self.error_message if self.error_message else f"String length out of bounds ({', '.join(length_desc)})"
            )
            raise ValidationError(variable_name=context.name, value=context.coerced_value, reason=reason)


class CustomValidationRule(ValidationRule):
    """Executes custom validator function."""

    def __init__(
        self,
        validator: Callable[[Any], bool],
        error_message: Optional[str] = None,
    ):
        """Initialize custom validation rule.

        Args:
            validator: Function that takes value and returns True if valid
            error_message: Custom error message
        """
        super().__init__(error_message)
        self.validator = validator

    def validate(self, context: ValidationContext) -> None:
        """Execute custom validator function."""
        from tripwire.exceptions import ValidationError

        try:
            result = self.validator(context.coerced_value)
            if not result:
                reason = self.error_message if self.error_message else "Custom validation failed"
                raise ValidationError(
                    variable_name=context.name,
                    value=context.coerced_value,
                    reason=reason,
                )
        except ValidationError:
            raise  # Re-raise ValidationError as-is
        except Exception as e:
            reason = self.error_message if self.error_message else f"Custom validation error: {e}"
            raise ValidationError(
                variable_name=context.name,
                value=context.coerced_value,
                reason=reason,
            )


class ValidationOrchestrator:
    """Orchestrates validation rule execution (Chain of Responsibility).

    This class manages a chain of validation rules and executes them in order.
    If any rule fails, execution stops and a ValidationError is raised.

    Example:
        >>> orchestrator = (
        ...     ValidationOrchestrator()
        ...     .add_rule(FormatValidationRule("email"))
        ...     .add_rule(LengthValidationRule(min_length=5))
        ... )
        >>> context = ValidationContext(
        ...     name="EMAIL",
        ...     raw_value="test@example.com",
        ...     coerced_value="test@example.com",
        ...     expected_type=str
        ... )
        >>> orchestrator.validate(context)
    """

    def __init__(self) -> None:
        """Initialize empty validation chain."""
        self.rules: List[ValidationRule] = []

    def add_rule(self, rule: ValidationRule) -> ValidationOrchestrator:
        """Add validation rule to chain (builder pattern).

        Args:
            rule: Validation rule to add

        Returns:
            Self for method chaining
        """
        self.rules.append(rule)
        return self

    def validate(self, context: ValidationContext) -> None:
        """Execute all validation rules in order.

        Args:
            context: Validation context with value and metadata

        Raises:
            ValidationError: If any rule fails
        """
        for rule in self.rules:
            rule.validate(context)
