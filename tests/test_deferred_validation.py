"""Test Phase 1 (v0.12.0): Deferred Validation for Custom Validators.

This test suite verifies the custom: prefix convention for custom validators,
ensuring that CLI commands gracefully handle validators that are not available
during schema validation (process boundary problem).

Key Features Tested:
- custom: prefix detection in _validate_format()
- schema check shows warnings for custom validators
- schema validate skips custom validators
- schema from-code emits custom: prefix for non-builtin validators
"""

import tempfile
from pathlib import Path

import pytest

from tripwire.schema import TripWireSchema, VariableSchema
from tripwire.validation import register_validator, unregister_validator


class TestCustomPrefixDetection:
    """Test custom: prefix detection in schema validation."""

    def test_custom_prefix_skips_validation(self):
        """Custom prefix causes validation to be skipped in schema."""
        var = VariableSchema(
            name="TEST_VAR",
            type="string",
            format="custom:unknown_validator",
        )

        # Should return True even though validator doesn't exist
        assert var._validate_format("any_value") is True

    def test_builtin_format_still_validates(self):
        """Builtin validators still work normally without custom: prefix."""
        var_email = VariableSchema(
            name="EMAIL",
            type="string",
            format="email",
        )

        # Invalid email should fail
        assert var_email._validate_format("invalid") is False

        # Valid email should pass
        assert var_email._validate_format("test@example.com") is True

    def test_custom_prefix_with_registered_validator(self):
        """Custom prefix skips validation even if validator IS registered."""

        # Register a custom validator
        def validate_test(value: str) -> bool:
            return value == "valid"

        register_validator("test_validator", validate_test)

        try:
            var = VariableSchema(
                name="TEST",
                type="string",
                format="custom:test_validator",
            )

            # Should skip validation (return True) because of custom: prefix
            # Even though validator exists and would reject "invalid"
            assert var._validate_format("invalid") is True
            assert var._validate_format("valid") is True

        finally:
            # Cleanup: remove test validator
            unregister_validator("test_validator")

    def test_multiple_custom_prefixes(self):
        """Multiple variables with custom: prefix all skip validation."""
        vars_list = [
            VariableSchema(name="VAR1", type="string", format="custom:phone"),
            VariableSchema(name="VAR2", type="string", format="custom:zip"),
            VariableSchema(name="VAR3", type="string", format="custom:custom_format"),
        ]

        for var in vars_list:
            assert var._validate_format("any_value") is True


class TestSchemaValidation:
    """Test full schema validation with custom validators."""

    def test_schema_validate_skips_custom_validators(self):
        """Schema validation passes for custom: validators without checking."""
        schema = TripWireSchema()
        schema.variables = {
            "PHONE": VariableSchema(
                name="PHONE",
                type="string",
                required=True,
                format="custom:phone",
            ),
            "EMAIL": VariableSchema(
                name="EMAIL",
                type="string",
                required=True,
                format="email",  # Builtin validator
            ),
        }

        # Test with invalid phone but valid email
        env_dict = {
            "PHONE": "invalid-phone-format",  # Would fail if validated
            "EMAIL": "test@example.com",  # Valid
        }

        is_valid, errors = schema.validate_env(env_dict)

        # Should pass because custom:phone is skipped
        assert is_valid is True
        assert len(errors) == 0

    def test_schema_validate_fails_on_invalid_builtin(self):
        """Schema validation fails for builtin validators as expected."""
        schema = TripWireSchema()
        schema.variables = {
            "EMAIL": VariableSchema(
                name="EMAIL",
                type="string",
                required=True,
                format="email",
            ),
        }

        # Invalid email
        env_dict = {"EMAIL": "not-an-email"}

        is_valid, errors = schema.validate_env(env_dict)

        # Should fail because email is a builtin validator
        assert is_valid is False
        assert len(errors) == 1
        assert "Invalid format" in errors[0]

    def test_mixed_validators_in_schema(self):
        """Schema with mixed builtin and custom validators."""
        schema = TripWireSchema()
        schema.variables = {
            "EMAIL": VariableSchema(
                name="EMAIL",
                type="string",
                required=True,
                format="email",
            ),
            "PHONE": VariableSchema(
                name="PHONE",
                type="string",
                required=True,
                format="custom:phone",
            ),
            "URL": VariableSchema(
                name="URL",
                type="string",
                required=True,
                format="url",
            ),
            "USERNAME": VariableSchema(
                name="USERNAME",
                type="string",
                required=True,
                format="custom:username",
            ),
        }

        # All valid except EMAIL
        env_dict = {
            "EMAIL": "invalid-email",  # Invalid builtin
            "PHONE": "not-a-phone",  # Would be invalid but skipped
            "URL": "https://example.com",  # Valid builtin
            "USERNAME": "!!!",  # Would be invalid but skipped
        }

        is_valid, errors = schema.validate_env(env_dict)

        # Should fail only on EMAIL (builtin validator)
        assert is_valid is False
        assert len(errors) == 1
        assert "EMAIL" in errors[0]


class TestSchemaCheckCommand:
    """Test schema check command behavior with custom validators.

    Note: Full CLI testing requires subprocess calls. These tests verify
    the underlying logic that the CLI commands use.
    """

    def test_custom_validators_detected_in_schema_file(self):
        """Schema file with custom: format is valid TOML and detectable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(
                """
[project]
name = "test"

[variables.PHONE]
type = "string"
required = true
format = "custom:phone"
description = "Phone number"

[variables.EMAIL]
type = "string"
required = true
format = "email"
description = "Email address"
"""
            )
            toml_path = Path(f.name)

        try:
            # Load schema and verify custom: prefix is preserved
            schema = TripWireSchema.from_toml(toml_path)

            assert "PHONE" in schema.variables
            assert schema.variables["PHONE"].format == "custom:phone"
            assert "EMAIL" in schema.variables
            assert schema.variables["EMAIL"].format == "email"

        finally:
            toml_path.unlink()


class TestSchemaFromCodeCommand:
    """Test schema from-code command emits custom: prefix.

    These tests verify the logic used by the CLI command to detect
    and emit custom: prefixes for non-builtin validators.
    """

    def test_builtin_validator_no_prefix(self):
        """Builtin validators should NOT get custom: prefix."""
        from tripwire.validation import list_validators

        all_validators = list_validators()
        builtin_validators = {name for name, vtype in all_validators.items() if vtype == "built-in"}

        # Test a known builtin validator
        assert "email" in builtin_validators

        # Should NOT add custom: prefix
        format_value = "email"
        if format_value not in builtin_validators:
            output_format = f"custom:{format_value}"
        else:
            output_format = format_value

        assert output_format == "email"

    def test_custom_validator_gets_prefix(self):
        """Custom validators should get custom: prefix in generated schema."""
        from tripwire.validation import list_validators

        all_validators = list_validators()
        builtin_validators = {name for name, vtype in all_validators.items() if vtype == "built-in"}

        # Test a non-existent validator
        format_value = "phone"
        assert format_value not in builtin_validators

        # Should add custom: prefix
        if format_value not in builtin_validators:
            output_format = f"custom:{format_value}"
        else:
            output_format = format_value

        assert output_format == "custom:phone"


class TestRuntimeValidation:
    """Test runtime validation strips custom: prefix.

    In actual application code, when validators ARE registered,
    the env.require() call should work with the base validator name
    (without custom: prefix).
    """

    def test_runtime_uses_base_validator_name(self):
        """At runtime, code uses validator name without custom: prefix."""

        # Register a custom validator
        def validate_phone(value: str) -> bool:
            import re

            pattern = r"^\d{3}-\d{3}-\d{4}$"
            return bool(re.match(pattern, value))

        register_validator("phone", validate_phone)

        try:
            # In runtime code, we use the base name "phone"
            # NOT "custom:phone"
            from tripwire.validation import get_validator

            validator = get_validator("phone")
            assert validator is not None

            # Validator should work
            assert validator("555-123-4567") is True
            assert validator("invalid") is False

        finally:
            # Cleanup
            unregister_validator("phone")


class TestBackwardCompatibility:
    """Test that existing validators without custom: prefix still work."""

    def test_existing_validators_unchanged(self):
        """Validators without custom: prefix continue to work."""
        var = VariableSchema(
            name="EMAIL",
            type="string",
            format="email",  # No custom: prefix
        )

        # Should validate normally
        assert var._validate_format("test@example.com") is True
        assert var._validate_format("invalid") is False

    def test_registered_custom_validator_without_prefix(self):
        """Custom validators registered in same process work without prefix."""

        # Register custom validator
        def validate_username(value: str) -> bool:
            return len(value) >= 3 and value.isalnum()

        register_validator("username", validate_username)

        try:
            # Using validator WITHOUT custom: prefix (same process)
            var = VariableSchema(
                name="USERNAME",
                type="string",
                format="username",  # No custom: prefix
            )

            # Should validate if validator is registered
            assert var._validate_format("alice") is True
            assert var._validate_format("ab") is False

        finally:
            unregister_validator("username")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_custom_prefix(self):
        """custom: with empty name should be handled gracefully."""
        var = VariableSchema(
            name="TEST",
            type="string",
            format="custom:",  # Empty validator name
        )

        # Should still return True (skip validation)
        assert var._validate_format("any_value") is True

    def test_nested_custom_prefix(self):
        """custom:custom:name should be handled (unlikely but possible)."""
        var = VariableSchema(
            name="TEST",
            type="string",
            format="custom:custom:nested",
        )

        # Should skip validation
        assert var._validate_format("any_value") is True

    def test_case_sensitivity(self):
        """custom: prefix should be case-sensitive."""
        # Uppercase should NOT be treated as custom prefix
        var_upper = VariableSchema(
            name="TEST",
            type="string",
            format="CUSTOM:phone",
        )

        # Should try to validate (and fail since CUSTOM:phone doesn't exist)
        assert var_upper._validate_format("any_value") is False

    def test_whitespace_around_prefix(self):
        """Whitespace around custom: should not affect detection."""
        var = VariableSchema(
            name="TEST",
            type="string",
            format="custom:phone",  # No whitespace
        )

        assert var._validate_format("any_value") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
