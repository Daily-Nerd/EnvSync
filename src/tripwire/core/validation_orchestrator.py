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
            reason = self.error_message if self.error_message else f"Does not match pattern: {self.pattern}"
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
            reason = self.error_message if self.error_message else f"Not in allowed choices: {self.choices}"
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
                range_desc.append(f">= {self.min_val}")
            if self.max_val is not None:
                range_desc.append(f"<= {self.max_val}")

            reason = self.error_message if self.error_message else f"Out of range: must be {' and '.join(range_desc)}"
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

        length = len(context.coerced_value)
        if self.min_length is not None and length < self.min_length:
            reason = (
                self.error_message
                if self.error_message
                else f"String too short: must be at least {self.min_length} characters"
            )
            raise ValidationError(variable_name=context.name, value=context.coerced_value, reason=reason)

        if self.max_length is not None and length > self.max_length:
            reason = (
                self.error_message
                if self.error_message
                else f"String too long: must be at most {self.max_length} characters"
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


class URLComponentsValidationRule(ValidationRule):
    """Validates URL components (protocol, port, path, query params).

    This rule provides fine-grained control over URL structure for security
    and API requirements. Use it to enforce HTTPS-only, specific ports,
    path patterns, and query parameter policies.

    Example:
        >>> # Enforce HTTPS-only API URLs with versioning
        >>> rule = URLComponentsValidationRule(
        ...     protocols=["https"],
        ...     allowed_ports=[443, 8443],
        ...     required_path="^/api/v[0-9]+/",
        ...     required_params=["api_key"],
        ...     forbidden_params=["debug"]
        ... )
    """

    def __init__(
        self,
        protocols: Optional[List[str]] = None,
        allowed_ports: Optional[List[int]] = None,
        forbidden_ports: Optional[List[int]] = None,
        required_path: Optional[str] = None,
        required_params: Optional[List[str]] = None,
        forbidden_params: Optional[List[str]] = None,
        error_message: Optional[str] = None,
    ):
        """Initialize URL components validation rule.

        Args:
            protocols: Whitelist of allowed protocols/schemes (e.g., ["https", "wss"])
            allowed_ports: Whitelist of allowed ports (e.g., [443, 8443])
            forbidden_ports: Blacklist of forbidden ports (e.g., [22, 3389])
            required_path: Regex pattern that path must match (e.g., "^/api/")
            required_params: Query parameters that must be present (e.g., ["api_key"])
            forbidden_params: Query parameters that must not be present (e.g., ["debug"])
            error_message: Custom error message (overrides detailed validation messages)
        """
        super().__init__(error_message)
        self.protocols = protocols
        self.allowed_ports = allowed_ports
        self.forbidden_ports = forbidden_ports
        self.required_path = required_path
        self.required_params = required_params
        self.forbidden_params = forbidden_params

    def validate(self, context: ValidationContext) -> None:
        """Validate URL components."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_url_components

        # Only validate string values (check coerced_value type like other rules)
        if not isinstance(context.coerced_value, str):
            return

        is_valid, error_msg = validate_url_components(
            context.raw_value,
            protocols=self.protocols,
            allowed_ports=self.allowed_ports,
            forbidden_ports=self.forbidden_ports,
            required_path=self.required_path,
            required_params=self.required_params,
            forbidden_params=self.forbidden_params,
        )

        if not is_valid:
            # Use custom error message if provided, otherwise use validation error message
            # Fallback to generic message if error_msg is somehow None (defensive)
            reason = self.error_message if self.error_message else (error_msg or "URL validation failed")
            raise ValidationError(
                variable_name=context.name,
                value=context.raw_value,
                reason=reason,
            )


class DateTimeValidationRule(ValidationRule):
    """Validates datetime strings with format and range requirements.

    This rule provides flexible datetime validation for timestamps,
    scheduled tasks, expiration dates, and time-sensitive configurations.

    Example:
        >>> # Enforce ISO 8601 with timezone
        >>> rule = DateTimeValidationRule(
        ...     formats=["ISO8601"],
        ...     require_timezone=True,
        ...     min_datetime="2020-01-01T00:00:00Z",
        ...     max_datetime="2030-12-31T23:59:59Z"
        ... )
    """

    def __init__(
        self,
        formats: Optional[List[str]] = None,
        require_timezone: Optional[bool] = None,
        min_datetime: Optional[str] = None,
        max_datetime: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Initialize datetime validation rule.

        Args:
            formats: List of accepted datetime formats. Use "ISO8601" for ISO 8601,
                or provide strptime format strings (e.g., "%Y-%m-%d %H:%M:%S").
                Default: ["ISO8601"]
            require_timezone: If True, require timezone-aware datetimes.
                If False, require timezone-naive datetimes. If None, both allowed.
            min_datetime: Minimum allowed datetime (ISO 8601 format).
                Example: "2020-01-01T00:00:00Z"
            max_datetime: Maximum allowed datetime (ISO 8601 format).
                Example: "2030-12-31T23:59:59Z"
            error_message: Custom error message (overrides detailed validation messages)
        """
        super().__init__(error_message)
        self.formats = formats
        self.require_timezone = require_timezone
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime

    def validate(self, context: ValidationContext) -> None:
        """Validate datetime string."""
        from tripwire.exceptions import ValidationError
        from tripwire.validation import validate_datetime

        # Only validate string values (check coerced_value type like other rules)
        if not isinstance(context.coerced_value, str):
            return

        is_valid, error_msg = validate_datetime(
            context.raw_value,
            formats=self.formats,
            require_timezone=self.require_timezone,
            min_datetime=self.min_datetime,
            max_datetime=self.max_datetime,
        )

        if not is_valid:
            # Use custom error message if provided, otherwise use validation error message
            # Fallback to generic message if error_msg is somehow None (defensive)
            reason = self.error_message if self.error_message else (error_msg or "DateTime validation failed")
            raise ValidationError(
                variable_name=context.name,
                value=context.raw_value,
                reason=reason,
            )


class ValidationOrchestrator:
    """Orchestrates validation rule execution (Chain of Responsibility).

    This class manages a chain of validation rules and executes them in order.

    Modes:
        - collect_errors=False (default): Fail-fast - stops at first error
        - collect_errors=True: Collects all errors and stores them for batch reporting

    Example:
        >>> orchestrator = (
        ...     ValidationOrchestrator(collect_errors=True)
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
        >>> errors = orchestrator.get_collected_errors()
    """

    def __init__(self, collect_errors: bool = False) -> None:
        """Initialize validation chain with optional error collection.

        Args:
            collect_errors: If True, collect all errors instead of failing fast.
                           If False, raise immediately on first error (legacy behavior).
        """
        self.rules: List[ValidationRule] = []
        self.collect_errors = collect_errors
        self.collected_errors: List[Any] = []  # Will be List[ValidationError]

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

        Behavior depends on collect_errors mode:
        - If collect_errors=False: Raises ValidationError on first failure (fail-fast)
        - If collect_errors=True: Collects all errors, accessible via get_collected_errors()

        Args:
            context: Validation context with value and metadata

        Raises:
            ValidationError: If any rule fails (only in fail-fast mode)
        """
        if self.collect_errors:
            # Error collection mode: try all rules, collect failures
            for rule in self.rules:
                try:
                    rule.validate(context)
                except Exception as e:
                    # Import here to avoid circular dependency
                    from tripwire.exceptions import ValidationError

                    # Only collect ValidationError instances
                    if isinstance(e, ValidationError):
                        self.collected_errors.append(e)
                    else:
                        # Re-raise non-validation errors (system errors)
                        raise
        else:
            # Fail-fast mode: raise immediately on first error (legacy behavior)
            for rule in self.rules:
                rule.validate(context)

    def get_collected_errors(self) -> List[Any]:
        """Get all validation errors collected during validation.

        Returns:
            List of ValidationError instances collected (empty if none or not in collection mode)
        """
        return self.collected_errors

    def has_errors(self) -> bool:
        """Check if any validation errors were collected.

        Returns:
            True if errors were collected, False otherwise
        """
        return len(self.collected_errors) > 0

    def clear_errors(self) -> None:
        """Clear collected errors (useful for reusing orchestrator)."""
        self.collected_errors.clear()
