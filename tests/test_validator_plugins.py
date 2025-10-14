"""Tests for custom validator plugin system."""

import re

import pytest

from tripwire.validation import (
    clear_custom_validators,
    get_validator,
    list_validators,
    register_validator,
    register_validator_decorator,
    unregister_validator,
)


class TestRegisterValidator:
    """Test register_validator function."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_register_simple_validator(self):
        """Test registering a simple validator."""

        def validate_test(value: str) -> bool:
            return value == "test"

        register_validator("test_format", validate_test)

        validator = get_validator("test_format")
        assert validator is not None
        assert validator("test") is True
        assert validator("other") is False

    def test_register_phone_validator(self):
        """Test registering a phone number validator."""

        def validate_phone(value: str) -> bool:
            pattern = r"^\d{3}-\d{3}-\d{4}$"
            return bool(re.match(pattern, value))

        register_validator("phone", validate_phone)

        validator = get_validator("phone")
        assert validator is not None
        assert validator("555-123-4567") is True
        assert validator("5551234567") is False
        assert validator("555-12-4567") is False

    def test_register_cannot_override_builtin(self):
        """Test that built-in validators cannot be overridden."""

        def my_validator(value: str) -> bool:
            return True

        with pytest.raises(ValueError, match="conflicts with built-in validator"):
            register_validator("email", my_validator)

        with pytest.raises(ValueError, match="conflicts with built-in validator"):
            register_validator("url", my_validator)

    def test_register_multiple_validators(self):
        """Test registering multiple validators."""

        def validate_a(value: str) -> bool:
            return value.startswith("a")

        def validate_b(value: str) -> bool:
            return value.startswith("b")

        register_validator("starts_with_a", validate_a)
        register_validator("starts_with_b", validate_b)

        validator_a = get_validator("starts_with_a")
        validator_b = get_validator("starts_with_b")

        assert validator_a is not None
        assert validator_b is not None
        assert validator_a("apple") is True
        assert validator_b("banana") is True

    def test_register_can_override_custom_validator(self):
        """Test that custom validators can be overridden."""

        def validator_v1(value: str) -> bool:
            return value == "v1"

        def validator_v2(value: str) -> bool:
            return value == "v2"

        register_validator("test", validator_v1)
        validator = get_validator("test")
        assert validator is not None
        assert validator("v1") is True

        # Override with v2
        register_validator("test", validator_v2)
        validator = get_validator("test")
        assert validator is not None
        assert validator("v2") is True
        assert validator("v1") is False


class TestRegisterValidatorDecorator:
    """Test register_validator_decorator function."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_decorator_registration(self):
        """Test registering validator with decorator."""

        @register_validator_decorator("zip_code")
        def validate_zip(value: str) -> bool:
            pattern = r"^\d{5}$"
            return bool(re.match(pattern, value))

        validator = get_validator("zip_code")
        assert validator is not None
        assert validator("12345") is True
        assert validator("1234") is False

    def test_decorator_returns_function(self):
        """Test that decorator returns the original function."""

        @register_validator_decorator("test")
        def validate_test(value: str) -> bool:
            return True

        # Function should still be callable
        assert validate_test("anything") is True

    def test_multiple_decorators(self):
        """Test registering multiple validators with decorators."""

        @register_validator_decorator("alpha")
        def validate_alpha(value: str) -> bool:
            return value.isalpha()

        @register_validator_decorator("numeric")
        def validate_numeric(value: str) -> bool:
            return value.isnumeric()

        alpha_validator = get_validator("alpha")
        numeric_validator = get_validator("numeric")

        assert alpha_validator is not None
        assert numeric_validator is not None
        assert alpha_validator("abc") is True
        assert numeric_validator("123") is True


class TestUnregisterValidator:
    """Test unregister_validator function."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_unregister_existing_validator(self):
        """Test unregistering an existing validator."""

        def validate_test(value: str) -> bool:
            return True

        register_validator("test", validate_test)
        assert get_validator("test") is not None

        result = unregister_validator("test")
        assert result is True
        assert get_validator("test") is None

    def test_unregister_nonexistent_validator(self):
        """Test unregistering a validator that doesn't exist."""
        result = unregister_validator("nonexistent")
        assert result is False

    def test_cannot_unregister_builtin(self):
        """Test that built-in validators cannot be unregistered."""
        result = unregister_validator("email")
        assert result is False
        # Built-in validator should still work
        assert get_validator("email") is not None


class TestGetValidator:
    """Test get_validator function."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_get_builtin_validator(self):
        """Test getting built-in validators."""
        assert get_validator("email") is not None
        assert get_validator("url") is not None
        assert get_validator("uuid") is not None
        assert get_validator("ipv4") is not None
        assert get_validator("postgresql") is not None

    def test_get_custom_validator(self):
        """Test getting custom validators."""

        def validate_test(value: str) -> bool:
            return True

        register_validator("test", validate_test)
        validator = get_validator("test")
        assert validator is not None
        assert validator is validate_test

    def test_get_nonexistent_validator(self):
        """Test getting a validator that doesn't exist."""
        validator = get_validator("nonexistent")
        assert validator is None

    def test_builtin_takes_precedence(self):
        """Test that built-in validators take precedence over custom."""
        # This shouldn't be possible due to register_validator checks,
        # but test the get_validator logic directly

        def custom_email(value: str) -> bool:
            return False

        # Can't actually register due to check, so just verify precedence logic
        email_validator = get_validator("email")
        assert email_validator is not None
        # The built-in email validator should return True for valid emails
        assert email_validator("test@example.com") is True


class TestListValidators:
    """Test list_validators function."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_list_builtin_validators(self):
        """Test listing built-in validators."""
        validators = list_validators()

        assert "email" in validators
        assert validators["email"] == "built-in"
        assert "url" in validators
        assert validators["url"] == "built-in"
        assert "uuid" in validators
        assert "ipv4" in validators
        assert "postgresql" in validators

    def test_list_includes_custom_validators(self):
        """Test that custom validators appear in the list."""

        def validate_test(value: str) -> bool:
            return True

        register_validator("test", validate_test)

        validators = list_validators()
        assert "test" in validators
        assert validators["test"] == "custom"

    def test_list_mixed_validators(self):
        """Test listing both built-in and custom validators."""

        def validate_custom1(value: str) -> bool:
            return True

        def validate_custom2(value: str) -> bool:
            return True

        register_validator("custom1", validate_custom1)
        register_validator("custom2", validate_custom2)

        validators = list_validators()

        # Check built-ins
        assert validators["email"] == "built-in"
        assert validators["url"] == "built-in"

        # Check customs
        assert validators["custom1"] == "custom"
        assert validators["custom2"] == "custom"


class TestClearCustomValidators:
    """Test clear_custom_validators function."""

    def test_clear_removes_all_custom_validators(self):
        """Test that clear removes all custom validators."""

        def validate_test1(value: str) -> bool:
            return True

        def validate_test2(value: str) -> bool:
            return True

        register_validator("test1", validate_test1)
        register_validator("test2", validate_test2)

        assert get_validator("test1") is not None
        assert get_validator("test2") is not None

        clear_custom_validators()

        assert get_validator("test1") is None
        assert get_validator("test2") is None

    def test_clear_preserves_builtin_validators(self):
        """Test that clear doesn't affect built-in validators."""
        clear_custom_validators()

        assert get_validator("email") is not None
        assert get_validator("url") is not None


class TestValidatorIntegration:
    """Integration tests for validator plugin system."""

    def setup_method(self):
        """Clear custom validators before each test."""
        clear_custom_validators()

    def teardown_method(self):
        """Clear custom validators after each test."""
        clear_custom_validators()

    def test_complex_validator_scenario(self):
        """Test complex scenario with multiple validators."""

        @register_validator_decorator("hex_color")
        def validate_hex_color(value: str) -> bool:
            pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
            return bool(re.match(pattern, value))

        @register_validator_decorator("semantic_version")
        def validate_semver(value: str) -> bool:
            pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
            return bool(re.match(pattern, value))

        # Test validators
        color_validator = get_validator("hex_color")
        version_validator = get_validator("semantic_version")

        assert color_validator is not None
        assert version_validator is not None

        # Valid cases
        assert color_validator("#FF5733") is True
        assert color_validator("#FFF") is True
        assert version_validator("1.0.0") is True
        assert version_validator("0.0.1") is True

        # Invalid cases
        assert color_validator("#GGGGGG") is False
        assert color_validator("FF5733") is False
        assert version_validator("1.0") is False
        assert version_validator("v1.0.0") is False

    def test_validator_with_tripwire_core(self):
        """Test using custom validators with TripWire.require()."""
        import os

        from tripwire import env

        @register_validator_decorator("phone")
        def validate_phone(value: str) -> bool:
            pattern = r"^\d{3}-\d{3}-\d{4}$"
            return bool(re.match(pattern, value))

        # Set environment variable
        os.environ["TEST_PHONE"] = "555-123-4567"

        # Should work with custom validator
        phone = env.require("TEST_PHONE", format="phone")
        assert phone == "555-123-4567"

        # Cleanup
        del os.environ["TEST_PHONE"]

    def test_validator_error_with_unknown_format(self):
        """Test that using unknown format raises appropriate error."""
        import os

        from tripwire import TripWire
        from tripwire.exceptions import ValidationError

        os.environ["TEST_VAR"] = "value"

        # Use fail-fast mode for clear error testing
        env_test = TripWire(collect_errors=False, auto_load=False)

        with pytest.raises(ValidationError, match="Unknown format validator"):
            env_test.require("TEST_VAR", format="nonexistent_format")

        del os.environ["TEST_VAR"]
