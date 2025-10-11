"""Tests for ValidationOrchestrator and validation rules."""

import pytest

from tripwire.core.validation_orchestrator import (
    ChoicesValidationRule,
    CustomValidationRule,
    FormatValidationRule,
    LengthValidationRule,
    PatternValidationRule,
    RangeValidationRule,
    ValidationContext,
    ValidationOrchestrator,
    ValidationRule,
)
from tripwire.exceptions import ValidationError


class TestValidationContext:
    """Test ValidationContext dataclass."""

    def test_create_context(self):
        """Test creating validation context."""
        context = ValidationContext(name="TEST_VAR", raw_value="42", coerced_value=42, expected_type=int)
        assert context.name == "TEST_VAR"
        assert context.raw_value == "42"
        assert context.coerced_value == 42
        assert context.expected_type == int

    def test_context_with_string(self):
        """Test context with string value."""
        context = ValidationContext(
            name="NAME",
            raw_value="alice",
            coerced_value="alice",
            expected_type=str,
        )
        assert context.name == "NAME"
        assert context.raw_value == "alice"
        assert context.coerced_value == "alice"
        assert context.expected_type == str


class TestFormatValidationRule:
    """Test FormatValidationRule."""

    def test_valid_email(self):
        """Test validation passes for valid email."""
        rule = FormatValidationRule("email")
        context = ValidationContext(
            name="EMAIL",
            raw_value="test@example.com",
            coerced_value="test@example.com",
            expected_type=str,
        )
        rule.validate(context)  # Should not raise

    def test_invalid_email(self):
        """Test validation fails for invalid email."""
        rule = FormatValidationRule("email")
        context = ValidationContext(
            name="EMAIL",
            raw_value="not-an-email",
            coerced_value="not-an-email",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Invalid format"):
            rule.validate(context)

    def test_valid_url(self):
        """Test validation passes for valid URL."""
        rule = FormatValidationRule("url")
        context = ValidationContext(
            name="API_URL",
            raw_value="https://api.example.com",
            coerced_value="https://api.example.com",
            expected_type=str,
        )
        rule.validate(context)

    def test_invalid_url(self):
        """Test validation fails for invalid URL."""
        rule = FormatValidationRule("url")
        context = ValidationContext(
            name="API_URL",
            raw_value="not-a-url",
            coerced_value="not-a-url",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Invalid format"):
            rule.validate(context)

    def test_unknown_format(self):
        """Test validation fails for unknown format."""
        rule = FormatValidationRule("unknown_format")
        context = ValidationContext(name="VAR", raw_value="value", coerced_value="value", expected_type=str)
        with pytest.raises(ValidationError, match="Unknown format validator"):
            rule.validate(context)

    def test_custom_error_message(self):
        """Test custom error message is used."""
        rule = FormatValidationRule("email", error_message="Invalid email address!")
        context = ValidationContext(name="EMAIL", raw_value="bad", coerced_value="bad", expected_type=str)
        with pytest.raises(ValidationError, match="Invalid email address!"):
            rule.validate(context)


class TestPatternValidationRule:
    """Test PatternValidationRule."""

    def test_valid_pattern(self):
        """Test validation passes for matching pattern."""
        rule = PatternValidationRule(r"^\d{3}-\d{3}-\d{4}$")
        context = ValidationContext(
            name="PHONE",
            raw_value="555-123-4567",
            coerced_value="555-123-4567",
            expected_type=str,
        )
        rule.validate(context)

    def test_invalid_pattern(self):
        """Test validation fails for non-matching pattern."""
        rule = PatternValidationRule(r"^\d{3}-\d{3}-\d{4}$")
        context = ValidationContext(
            name="PHONE",
            raw_value="invalid",
            coerced_value="invalid",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Does not match pattern"):
            rule.validate(context)

    def test_alphanumeric_pattern(self):
        """Test alphanumeric pattern validation."""
        rule = PatternValidationRule(r"^[A-Za-z0-9]+$")
        context = ValidationContext(name="CODE", raw_value="ABC123", coerced_value="ABC123", expected_type=str)
        rule.validate(context)

    def test_alphanumeric_pattern_invalid(self):
        """Test alphanumeric pattern fails with special chars."""
        rule = PatternValidationRule(r"^[A-Za-z0-9]+$")
        context = ValidationContext(
            name="CODE",
            raw_value="ABC-123",
            coerced_value="ABC-123",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Does not match pattern"):
            rule.validate(context)

    def test_custom_error_message(self):
        """Test custom error message for pattern validation."""
        rule = PatternValidationRule(r"^\d+$", error_message="Must be digits only!")
        context = ValidationContext(name="VAR", raw_value="abc", coerced_value="abc", expected_type=str)
        with pytest.raises(ValidationError, match="Must be digits only!"):
            rule.validate(context)


class TestChoicesValidationRule:
    """Test ChoicesValidationRule."""

    def test_valid_choice(self):
        """Test validation passes for valid choice."""
        rule = ChoicesValidationRule(["dev", "staging", "prod"])
        context = ValidationContext(name="ENV", raw_value="prod", coerced_value="prod", expected_type=str)
        rule.validate(context)

    def test_invalid_choice(self):
        """Test validation fails for invalid choice."""
        rule = ChoicesValidationRule(["dev", "staging", "prod"])
        context = ValidationContext(
            name="ENV",
            raw_value="invalid",
            coerced_value="invalid",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Not in allowed choices"):
            rule.validate(context)

    def test_single_choice(self):
        """Test validation with single choice."""
        rule = ChoicesValidationRule(["only"])
        context = ValidationContext(name="VAR", raw_value="only", coerced_value="only", expected_type=str)
        rule.validate(context)

    def test_case_sensitive_choices(self):
        """Test choices are case-sensitive."""
        rule = ChoicesValidationRule(["prod", "PROD"])
        context = ValidationContext(name="ENV", raw_value="prod", coerced_value="prod", expected_type=str)
        rule.validate(context)

        context2 = ValidationContext(name="ENV", raw_value="Prod", coerced_value="Prod", expected_type=str)
        with pytest.raises(ValidationError):
            rule.validate(context2)

    def test_custom_error_message(self):
        """Test custom error message for choices."""
        rule = ChoicesValidationRule(["a", "b"], error_message="Invalid environment!")
        context = ValidationContext(name="VAR", raw_value="c", coerced_value="c", expected_type=str)
        with pytest.raises(ValidationError, match="Invalid environment!"):
            rule.validate(context)


class TestRangeValidationRule:
    """Test RangeValidationRule."""

    def test_value_in_range(self):
        """Test validation passes for value in range."""
        rule = RangeValidationRule(min_val=0, max_val=100)
        context = ValidationContext(name="PORT", raw_value="50", coerced_value=50, expected_type=int)
        rule.validate(context)

    def test_value_below_min(self):
        """Test validation fails for value below minimum."""
        rule = RangeValidationRule(min_val=10)
        context = ValidationContext(name="PORT", raw_value="5", coerced_value=5, expected_type=int)
        with pytest.raises(ValidationError, match="Out of range"):
            rule.validate(context)

    def test_value_above_max(self):
        """Test validation fails for value above maximum."""
        rule = RangeValidationRule(max_val=100)
        context = ValidationContext(name="PORT", raw_value="150", coerced_value=150, expected_type=int)
        with pytest.raises(ValidationError, match="Out of range"):
            rule.validate(context)

    def test_value_at_min_boundary(self):
        """Test validation passes at minimum boundary."""
        rule = RangeValidationRule(min_val=10, max_val=100)
        context = ValidationContext(name="VAR", raw_value="10", coerced_value=10, expected_type=int)
        rule.validate(context)

    def test_value_at_max_boundary(self):
        """Test validation passes at maximum boundary."""
        rule = RangeValidationRule(min_val=10, max_val=100)
        context = ValidationContext(name="VAR", raw_value="100", coerced_value=100, expected_type=int)
        rule.validate(context)

    def test_float_range(self):
        """Test range validation with float values."""
        rule = RangeValidationRule(min_val=0.0, max_val=1.0)
        context = ValidationContext(name="RATIO", raw_value="0.5", coerced_value=0.5, expected_type=float)
        rule.validate(context)

    def test_non_numeric_skipped(self):
        """Test range validation skipped for non-numeric types."""
        rule = RangeValidationRule(min_val=0, max_val=100)
        context = ValidationContext(name="VAR", raw_value="string", coerced_value="string", expected_type=str)
        rule.validate(context)  # Should not raise (skipped for strings)

    def test_custom_error_message(self):
        """Test custom error message for range."""
        rule = RangeValidationRule(min_val=0, max_val=100, error_message="Bad range!")
        context = ValidationContext(name="VAR", raw_value="200", coerced_value=200, expected_type=int)
        with pytest.raises(ValidationError, match="Bad range!"):
            rule.validate(context)


class TestLengthValidationRule:
    """Test LengthValidationRule."""

    def test_length_in_range(self):
        """Test validation passes for length in range."""
        rule = LengthValidationRule(min_length=3, max_length=10)
        context = ValidationContext(name="NAME", raw_value="alice", coerced_value="alice", expected_type=str)
        rule.validate(context)

    def test_length_too_short(self):
        """Test validation fails for length below minimum."""
        rule = LengthValidationRule(min_length=5)
        context = ValidationContext(name="NAME", raw_value="ab", coerced_value="ab", expected_type=str)
        with pytest.raises(ValidationError, match="String too"):
            rule.validate(context)

    def test_length_too_long(self):
        """Test validation fails for length above maximum."""
        rule = LengthValidationRule(max_length=5)
        context = ValidationContext(
            name="NAME",
            raw_value="toolong",
            coerced_value="toolong",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="String too"):
            rule.validate(context)

    def test_length_at_min_boundary(self):
        """Test validation passes at minimum length boundary."""
        rule = LengthValidationRule(min_length=5, max_length=10)
        context = ValidationContext(name="VAR", raw_value="hello", coerced_value="hello", expected_type=str)
        rule.validate(context)

    def test_length_at_max_boundary(self):
        """Test validation passes at maximum length boundary."""
        rule = LengthValidationRule(min_length=5, max_length=10)
        context = ValidationContext(
            name="VAR",
            raw_value="helloworld",
            coerced_value="helloworld",
            expected_type=str,
        )
        rule.validate(context)

    def test_empty_string_min_length(self):
        """Test empty string fails minimum length."""
        rule = LengthValidationRule(min_length=1)
        context = ValidationContext(name="VAR", raw_value="", coerced_value="", expected_type=str)
        with pytest.raises(ValidationError, match="String too"):
            rule.validate(context)

    def test_non_string_skipped(self):
        """Test length validation skipped for non-string types."""
        rule = LengthValidationRule(min_length=1, max_length=10)
        context = ValidationContext(name="PORT", raw_value="42", coerced_value=42, expected_type=int)
        rule.validate(context)  # Should not raise (skipped for non-strings)

    def test_custom_error_message(self):
        """Test custom error message for length."""
        rule = LengthValidationRule(min_length=5, error_message="Too short!")
        context = ValidationContext(name="VAR", raw_value="hi", coerced_value="hi", expected_type=str)
        with pytest.raises(ValidationError, match="Too short!"):
            rule.validate(context)


class TestCustomValidationRule:
    """Test CustomValidationRule."""

    def test_validator_returns_true(self):
        """Test validation passes when validator returns True."""
        rule = CustomValidationRule(lambda x: x > 0)
        context = ValidationContext(name="VAR", raw_value="42", coerced_value=42, expected_type=int)
        rule.validate(context)

    def test_validator_returns_false(self):
        """Test validation fails when validator returns False."""
        rule = CustomValidationRule(lambda x: x > 0)
        context = ValidationContext(name="VAR", raw_value="-5", coerced_value=-5, expected_type=int)
        with pytest.raises(ValidationError, match="Custom validation failed"):
            rule.validate(context)

    def test_validator_with_complex_logic(self):
        """Test custom validator with complex logic."""

        def is_even_and_positive(x: int) -> bool:
            return x > 0 and x % 2 == 0

        rule = CustomValidationRule(is_even_and_positive)
        context = ValidationContext(name="VAR", raw_value="10", coerced_value=10, expected_type=int)
        rule.validate(context)

    def test_validator_raises_validation_error(self):
        """Test custom validator that raises ValidationError."""

        def validator(x):
            raise ValidationError(variable_name="VAR", value=x, reason="Custom error")

        rule = CustomValidationRule(validator)
        context = ValidationContext(name="VAR", raw_value="value", coerced_value="value", expected_type=str)
        with pytest.raises(ValidationError, match="Custom error"):
            rule.validate(context)

    def test_validator_raises_other_exception(self):
        """Test custom validator that raises other exception."""

        def validator(x):
            raise ValueError("Something went wrong")

        rule = CustomValidationRule(validator)
        context = ValidationContext(name="VAR", raw_value="value", coerced_value="value", expected_type=str)
        with pytest.raises(ValidationError, match="Custom validation error"):
            rule.validate(context)

    def test_custom_error_message(self):
        """Test custom error message for custom validator."""
        rule = CustomValidationRule(lambda x: x > 0, error_message="Must be positive!")
        context = ValidationContext(name="VAR", raw_value="-5", coerced_value=-5, expected_type=int)
        with pytest.raises(ValidationError, match="Must be positive!"):
            rule.validate(context)


class TestValidationOrchestrator:
    """Test ValidationOrchestrator."""

    def test_empty_orchestrator(self):
        """Test orchestrator with no rules passes."""
        orchestrator = ValidationOrchestrator()
        context = ValidationContext(name="VAR", raw_value="value", coerced_value="value", expected_type=str)
        orchestrator.validate(context)  # Should not raise

    def test_single_rule(self):
        """Test orchestrator with single rule."""
        orchestrator = ValidationOrchestrator()
        orchestrator.add_rule(FormatValidationRule("email"))

        context = ValidationContext(
            name="EMAIL",
            raw_value="test@example.com",
            coerced_value="test@example.com",
            expected_type=str,
        )
        orchestrator.validate(context)

    def test_multiple_rules_all_pass(self):
        """Test orchestrator with multiple rules all passing."""
        orchestrator = ValidationOrchestrator()
        orchestrator.add_rule(FormatValidationRule("email"))
        orchestrator.add_rule(PatternValidationRule(r".*@example\.com$"))
        orchestrator.add_rule(LengthValidationRule(min_length=5, max_length=50))

        context = ValidationContext(
            name="EMAIL",
            raw_value="test@example.com",
            coerced_value="test@example.com",
            expected_type=str,
        )
        orchestrator.validate(context)

    def test_multiple_rules_first_fails(self):
        """Test orchestrator stops at first failing rule."""
        orchestrator = ValidationOrchestrator()
        orchestrator.add_rule(FormatValidationRule("email"))  # Will fail
        orchestrator.add_rule(PatternValidationRule(r".*"))  # Would pass

        context = ValidationContext(
            name="EMAIL",
            raw_value="not-an-email",
            coerced_value="not-an-email",
            expected_type=str,
        )

        with pytest.raises(ValidationError, match="Invalid format"):
            orchestrator.validate(context)

    def test_multiple_rules_second_fails(self):
        """Test orchestrator continues until failure."""
        orchestrator = ValidationOrchestrator()
        orchestrator.add_rule(PatternValidationRule(r".*"))  # Passes (matches everything)
        orchestrator.add_rule(LengthValidationRule(min_length=100))  # Fails

        context = ValidationContext(name="VAR", raw_value="short", coerced_value="short", expected_type=str)

        with pytest.raises(ValidationError, match="String too"):
            orchestrator.validate(context)

    def test_builder_pattern(self):
        """Test builder pattern for adding rules."""
        orchestrator = (
            ValidationOrchestrator()
            .add_rule(RangeValidationRule(min_val=0, max_val=100))
            .add_rule(CustomValidationRule(lambda x: x % 2 == 0))
        )

        assert len(orchestrator.rules) == 2

        # Valid value (even number in range)
        context = ValidationContext(name="VAR", raw_value="50", coerced_value=50, expected_type=int)
        orchestrator.validate(context)

        # Invalid value (odd number)
        context2 = ValidationContext(name="VAR", raw_value="51", coerced_value=51, expected_type=int)
        with pytest.raises(ValidationError):
            orchestrator.validate(context2)

    def test_complex_validation_chain(self):
        """Test complex validation chain with many rules."""
        orchestrator = (
            ValidationOrchestrator()
            .add_rule(FormatValidationRule("email"))
            .add_rule(PatternValidationRule(r"^[a-z]+@[a-z]+\.[a-z]+$"))
            .add_rule(LengthValidationRule(min_length=10, max_length=50))
            .add_rule(CustomValidationRule(lambda x: "test" not in x.lower()))
        )

        # Valid email
        context = ValidationContext(
            name="EMAIL",
            raw_value="user@example.com",
            coerced_value="user@example.com",
            expected_type=str,
        )
        orchestrator.validate(context)

        # Invalid (contains "test")
        context2 = ValidationContext(
            name="EMAIL",
            raw_value="test@example.com",
            coerced_value="test@example.com",
            expected_type=str,
        )
        with pytest.raises(ValidationError, match="Custom validation"):
            orchestrator.validate(context2)

    def test_orchestrator_reusable(self):
        """Test orchestrator can validate multiple contexts."""
        orchestrator = ValidationOrchestrator()
        orchestrator.add_rule(RangeValidationRule(min_val=0, max_val=100))

        # First validation
        context1 = ValidationContext(name="VAR1", raw_value="50", coerced_value=50, expected_type=int)
        orchestrator.validate(context1)

        # Second validation
        context2 = ValidationContext(name="VAR2", raw_value="75", coerced_value=75, expected_type=int)
        orchestrator.validate(context2)

        # Third validation (fails)
        context3 = ValidationContext(name="VAR3", raw_value="150", coerced_value=150, expected_type=int)
        with pytest.raises(ValidationError):
            orchestrator.validate(context3)
