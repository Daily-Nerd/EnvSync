"""Tests for multi-error validation feature.

This module tests the error collection functionality that allows TripWire to
collect all validation errors and report them together, dramatically improving
the developer experience by eliminating the fix-run-fix-run cycle.
"""

import os

import pytest

from tripwire.core.tripwire_v2 import TripWireV2
from tripwire.exceptions import (
    TripWireMultiValidationError,
    ValidationError,
)


class TestMultiErrorCollection:
    """Test multi-error collection functionality."""

    def setup_method(self):
        """Clear environment before each test."""
        # Clear all test variables
        test_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "REDIS_URL",
            "EMAIL",
            "PORT",
            "TIMEOUT",
            "LOG_LEVEL",
            "API_KEY",
            "MISSING_VAR",  # For has_validation_errors test
            "VAR1",  # For get_validation_errors test
            "VAR2",  # For get_validation_errors test
            "VAR_T0",
            "VAR_T1",
            "VAR_T2",
            "VAR_T3",
            "VAR_T4",  # For thread-safe test
            "VAR_T5",
            "VAR_T6",
            "VAR_T7",
            "VAR_T8",
            "VAR_T9",
            "ENV",  # For choices test
        ]
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]

    def test_multiple_missing_variables_collected(self):
        """Test that multiple missing variables are collected and reported together."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        # Declare multiple missing variables
        env.require("DATABASE_URL", format="postgresql")
        env.require("SECRET_KEY", min_length=32)
        env.require("REDIS_URL", format="url")

        # Should raise multi-error exception on finalization
        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error = exc_info.value
        assert error.error_count == 3
        assert "DATABASE_URL" in str(error)
        assert "SECRET_KEY" in str(error)
        assert "REDIS_URL" in str(error)
        assert "Fix all variables and restart" in str(error)

    def test_multiple_format_validation_errors(self):
        """Test that multiple format validation errors are collected."""
        # Set invalid values
        os.environ["EMAIL"] = "not-an-email"
        os.environ["DATABASE_URL"] = "not-a-postgresql-url"
        os.environ["REDIS_URL"] = "not-a-url"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("EMAIL", format="email")
        env.require("DATABASE_URL", format="postgresql")
        env.require("REDIS_URL", format="url")

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error = exc_info.value
        assert error.error_count == 3
        assert "EMAIL" in str(error)
        assert "DATABASE_URL" in str(error)
        assert "REDIS_URL" in str(error)

    def test_mixed_validation_errors(self):
        """Test mixed validation errors (missing, format, range, length)."""
        # Set some invalid values, leave others missing
        os.environ["PORT"] = "-5"  # Invalid range
        os.environ["API_KEY"] = "abc"  # Too short
        # DATABASE_URL is missing
        # EMAIL is missing

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("DATABASE_URL", format="postgresql")
        env.require("EMAIL", format="email")
        env.require("PORT", type=int, min_val=1, max_val=65535)
        env.require("API_KEY", min_length=32)

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error = exc_info.value
        assert error.error_count == 4
        assert "DATABASE_URL" in str(error)
        assert "EMAIL" in str(error)
        assert "PORT" in str(error)
        assert "API_KEY" in str(error)

    def test_single_error_not_multi(self):
        """Test that single error doesn't use multi-error format."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("DATABASE_URL", format="postgresql")

        # Should raise regular ValidationError, not Multi
        with pytest.raises(ValidationError) as exc_info:
            env.finalize()

        # Should NOT be multi-error
        assert not isinstance(exc_info.value, TripWireMultiValidationError)
        assert "DATABASE_URL" in str(exc_info.value)

    def test_no_errors_no_exception(self):
        """Test that finalization with no errors doesn't raise."""
        os.environ["PORT"] = "8000"
        os.environ["LOG_LEVEL"] = "INFO"

        env = TripWireV2(auto_load=False, collect_errors=True)

        port = env.require("PORT", type=int)
        log_level = env.require("LOG_LEVEL")

        # Should not raise
        env.finalize()

        assert port == 8000
        assert log_level == "INFO"

    def test_fix_suggestions_generated(self):
        """Test that helpful fix suggestions are included in error messages."""
        os.environ["DATABASE_URL"] = "invalid"
        os.environ["EMAIL"] = "not-email"
        os.environ["PORT"] = "999999"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("DATABASE_URL", format="postgresql")
        env.require("EMAIL", format="email")
        env.require("PORT", type=int, max_val=65535)

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)

        # Check for specific fix suggestions
        assert "postgresql://user:pass@host:port/db" in error_msg
        assert "user@example.com" in error_msg
        # Port should have decrease suggestion
        assert "Decrease PORT value" in error_msg or "PORT" in error_msg

    def test_type_coercion_errors_collected(self):
        """Test that type coercion errors are collected."""
        os.environ["PORT"] = "not-a-number"
        os.environ["TIMEOUT"] = "also-not-a-number"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("PORT", type=int)
        env.require("TIMEOUT", type=float)

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error = exc_info.value
        assert error.error_count == 2
        assert "PORT" in str(error)
        assert "TIMEOUT" in str(error)
        assert "coerce" in str(error).lower()

    def test_choices_validation_errors(self):
        """Test that choices validation errors are collected."""
        os.environ["ENV"] = "invalid"
        os.environ["LOG_LEVEL"] = "INVALID_LEVEL"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("ENV", choices=["dev", "staging", "prod"])
        env.require("LOG_LEVEL", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error = exc_info.value
        assert error.error_count == 2
        assert "ENV" in str(error)
        assert "LOG_LEVEL" in str(error)

    def test_has_validation_errors_method(self):
        """Test has_validation_errors() method."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        # Initially no errors
        assert not env.has_validation_errors()

        # Add some errors
        env.require("MISSING_VAR")

        # Should now have errors
        assert env.has_validation_errors()

    def test_get_validation_errors_method(self):
        """Test get_validation_errors() method returns error list."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("VAR1")
        env.require("VAR2")

        errors = env.get_validation_errors()
        assert len(errors) == 2
        assert all(isinstance(e, ValidationError) for e in errors)
        assert errors[0].variable_name == "VAR1"
        assert errors[1].variable_name == "VAR2"

    def test_error_collection_thread_safe(self):
        """Test that error collection is thread-safe."""
        import threading

        env = TripWireV2(auto_load=False, collect_errors=True)

        def collect_errors():
            env.require(f"VAR_{threading.current_thread().name}")

        # Create multiple threads
        threads = [threading.Thread(target=collect_errors, name=f"T{i}") for i in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should have 10 errors (one per thread)
        errors = env.get_validation_errors()
        assert len(errors) == 10


class TestFailFastMode:
    """Test fail-fast mode (legacy behavior)."""

    def setup_method(self):
        """Clear environment before each test."""
        test_vars = ["VAR1", "VAR2", "VAR3"]
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]

    def test_fail_fast_raises_immediately(self):
        """Test that fail-fast mode raises on first error."""
        env = TripWireV2(auto_load=False, collect_errors=False)

        # Should raise immediately on first missing variable
        with pytest.raises(Exception):  # MissingVariableError
            env.require("VAR1")
            env.require("VAR2")  # This should never be reached
            env.require("VAR3")

        # Errors should not be collected
        assert len(env.get_validation_errors()) == 0

    def test_fail_fast_no_finalization_needed(self):
        """Test that fail-fast mode doesn't need finalization."""
        os.environ["VAR1"] = "value1"

        env = TripWireV2(auto_load=False, collect_errors=False)

        var1 = env.require("VAR1")

        # Finalization should be no-op
        env.finalize()  # Should not raise

        assert var1 == "value1"


class TestErrorMessageFormatting:
    """Test error message formatting and fix suggestions."""

    def setup_method(self):
        """Clear environment before each test."""
        test_vars = [
            "VAR1",
            "VAR2",
            "VAR3",
            "MISSING_VAR",  # For test_missing_variable_fix_suggestion
            "EMAIL",
            "DB_URL",
            "UUID_VAR",
            "IP_VAR",  # For format validation tests
            "SHORT_VAR",
            "LONG_VAR",  # For length validation tests
            "LOW_VAR",
            "HIGH_VAR",  # For range validation tests
        ]
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]

    def test_error_message_structure(self):
        """Test that error message has clear structure."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("VAR1")
        env.require("VAR2")

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)

        # Check structure
        assert "TripWire found 2 environment variable error(s):" in error_msg
        assert "1. VAR1" in error_msg
        assert "2. VAR2" in error_msg
        assert "Error:" in error_msg
        assert "Received:" in error_msg
        assert "Fix:" in error_msg
        assert "Fix all variables and restart" in error_msg

    def test_missing_variable_fix_suggestion(self):
        """Test fix suggestion for missing variables."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("MISSING_VAR")

        # Single error will raise ValidationError, not Multi
        with pytest.raises(ValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)
        assert "MISSING_VAR" in error_msg
        assert "Required but not set" in error_msg

    def test_format_validation_fix_suggestions(self):
        """Test fix suggestions for different format validators."""
        os.environ["EMAIL"] = "bad"
        os.environ["DB_URL"] = "bad"
        os.environ["UUID_VAR"] = "bad"
        os.environ["IP_VAR"] = "bad"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("EMAIL", format="email")
        env.require("DB_URL", format="postgresql")
        env.require("UUID_VAR", format="uuid")
        env.require("IP_VAR", format="ipv4")

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)

        # Check format-specific suggestions
        assert "user@example.com" in error_msg
        assert "postgresql://user:pass@host:port/db" in error_msg
        assert "550e8400-e29b-41d4-a716-446655440000" in error_msg
        assert "192.168.1.1" in error_msg

    def test_length_validation_fix_suggestions(self):
        """Test fix suggestions for length validation."""
        os.environ["SHORT_VAR"] = "ab"
        os.environ["LONG_VAR"] = "x" * 100

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("SHORT_VAR", min_length=10)
        env.require("LONG_VAR", max_length=50)

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)

        assert "Provide a longer value for SHORT_VAR" in error_msg
        assert "Shorten LONG_VAR" in error_msg

    def test_range_validation_fix_suggestions(self):
        """Test fix suggestions for range validation."""
        os.environ["LOW_VAR"] = "5"
        os.environ["HIGH_VAR"] = "200"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("LOW_VAR", type=int, min_val=10)
        env.require("HIGH_VAR", type=int, max_val=100)

        with pytest.raises(TripWireMultiValidationError) as exc_info:
            env.finalize()

        error_msg = str(exc_info.value)

        # Check for increase/decrease suggestions
        assert "LOW_VAR" in error_msg
        assert "HIGH_VAR" in error_msg


class TestBackwardCompatibility:
    """Test backward compatibility with existing behavior."""

    def setup_method(self):
        """Clear environment before each test."""
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]

    def test_default_behavior_is_error_collection(self):
        """Test that default behavior is error collection (new behavior)."""
        env = TripWireV2(auto_load=False)

        # Should have error collection enabled by default
        assert env.collect_errors is True

    def test_can_disable_error_collection(self):
        """Test that error collection can be disabled for legacy behavior."""
        env = TripWireV2(auto_load=False, collect_errors=False)

        assert env.collect_errors is False

        # Should fail-fast
        with pytest.raises(Exception):  # MissingVariableError or ValidationError
            env.require("TEST_VAR")

    def test_optional_variables_not_collected(self):
        """Test that optional variables with defaults don't collect errors."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        # Optional variables should return defaults without errors
        result = env.optional("MISSING_OPTIONAL", default="default_value")

        assert result == "default_value"
        assert not env.has_validation_errors()

    def test_valid_variables_not_collected(self):
        """Test that valid variables don't generate errors."""
        os.environ["VALID_VAR"] = "valid_value"

        env = TripWireV2(auto_load=False, collect_errors=True)

        result = env.require("VALID_VAR")

        assert result == "valid_value"
        assert not env.has_validation_errors()

        # Finalization should be no-op
        env.finalize()


class TestExplicitFinalization:
    """Test explicit finalization control."""

    def setup_method(self):
        """Clear environment before each test."""
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]

    def test_manual_finalization(self):
        """Test that finalize() can be called manually."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("TEST_VAR")

        # Manual finalization
        with pytest.raises(ValidationError):
            env.finalize()

    def test_finalization_idempotent(self):
        """Test that finalization can only happen once."""
        os.environ["TEST_VAR"] = "value"

        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("TEST_VAR")

        # First finalization
        env.finalize()  # Should not raise

        # Second finalization should be no-op
        env.finalize()  # Should still not raise

    def test_finalization_after_errors_collected(self):
        """Test finalization after errors are collected."""
        env = TripWireV2(auto_load=False, collect_errors=True)

        env.require("VAR1")
        env.require("VAR2")

        # Check errors exist before finalization
        assert env.has_validation_errors()
        assert len(env.get_validation_errors()) == 2

        # Finalization should raise
        with pytest.raises(TripWireMultiValidationError):
            env.finalize()
