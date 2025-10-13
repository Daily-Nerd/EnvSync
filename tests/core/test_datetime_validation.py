"""Tests for DateTime validation."""

import pytest

from tripwire.core.validation_orchestrator import (
    DateTimeValidationRule,
    ValidationContext,
)
from tripwire.exceptions import ValidationError
from tripwire.validation import validate_datetime


class TestValidateDatetime:
    """Tests for validate_datetime() helper function."""

    # ISO 8601 format tests
    def test_valid_iso8601_with_timezone(self):
        """Valid ISO 8601 datetime with timezone passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z")
        assert valid is True
        assert error is None

    def test_valid_iso8601_with_offset(self):
        """Valid ISO 8601 datetime with timezone offset passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00+05:30")
        assert valid is True
        assert error is None

    def test_valid_iso8601_without_timezone(self):
        """Valid ISO 8601 datetime without timezone passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00")
        assert valid is True
        assert error is None

    def test_valid_iso8601_date_only(self):
        """Valid ISO 8601 date-only passes."""
        valid, error = validate_datetime("2025-10-13")
        assert valid is True
        assert error is None

    def test_invalid_iso8601_format(self):
        """Invalid ISO 8601 format fails."""
        valid, error = validate_datetime("not-a-date")
        assert valid is False
        assert "does not match any accepted format" in error

    # Custom format tests
    def test_valid_custom_format_ymd_hms(self):
        """Valid datetime with custom format %Y-%m-%d %H:%M:%S."""
        valid, error = validate_datetime("2025-10-13 14:30:00", formats=["%Y-%m-%d %H:%M:%S"])
        assert valid is True
        assert error is None

    def test_valid_custom_format_dmy(self):
        """Valid date with custom format %d/%m/%Y."""
        valid, error = validate_datetime("13/10/2025", formats=["%d/%m/%Y"])
        assert valid is True
        assert error is None

    def test_valid_custom_format_us_style(self):
        """Valid date with US-style format %m/%d/%Y."""
        valid, error = validate_datetime("10/13/2025", formats=["%m/%d/%Y"])
        assert valid is True
        assert error is None

    def test_multiple_formats_first_matches(self):
        """Multiple formats, first format matches."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", formats=["ISO8601", "%Y-%m-%d"])
        assert valid is True
        assert error is None

    def test_multiple_formats_second_matches(self):
        """Multiple formats, second format matches."""
        valid, error = validate_datetime("13/10/2025", formats=["%Y-%m-%d", "%d/%m/%Y"])
        assert valid is True
        assert error is None

    def test_no_format_matches(self):
        """No format matches returns error."""
        valid, error = validate_datetime("2025-10-13", formats=["%d/%m/%Y", "%m/%d/%Y"])
        assert valid is False
        assert "does not match any accepted format" in error
        assert "%d/%m/%Y" in error
        assert "%m/%d/%Y" in error

    # Timezone requirement tests
    def test_require_timezone_with_timezone(self):
        """require_timezone=True passes with timezone."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", require_timezone=True)
        assert valid is True
        assert error is None

    def test_require_timezone_without_timezone(self):
        """require_timezone=True fails without timezone."""
        valid, error = validate_datetime("2025-10-13T14:30:00", require_timezone=True)
        assert valid is False
        assert "must include timezone information" in error

    def test_forbid_timezone_without_timezone(self):
        """require_timezone=False passes without timezone."""
        valid, error = validate_datetime("2025-10-13T14:30:00", require_timezone=False)
        assert valid is True
        assert error is None

    def test_forbid_timezone_with_timezone(self):
        """require_timezone=False fails with timezone."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", require_timezone=False)
        assert valid is False
        assert "must not include timezone information" in error

    def test_timezone_optional_both_allowed(self):
        """require_timezone=None allows both."""
        # With timezone
        valid, _ = validate_datetime("2025-10-13T14:30:00Z", require_timezone=None)
        assert valid is True

        # Without timezone
        valid, _ = validate_datetime("2025-10-13T14:30:00", require_timezone=None)
        assert valid is True

    # Date range tests - min_datetime
    def test_min_datetime_after_minimum(self):
        """Datetime after minimum passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", min_datetime="2020-01-01T00:00:00Z")
        assert valid is True
        assert error is None

    def test_min_datetime_equal_to_minimum(self):
        """Datetime equal to minimum passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", min_datetime="2025-10-13T14:30:00Z")
        assert valid is True
        assert error is None

    def test_min_datetime_before_minimum(self):
        """Datetime before minimum fails."""
        valid, error = validate_datetime("2020-01-01T00:00:00Z", min_datetime="2025-01-01T00:00:00Z")
        assert valid is False
        assert "is before minimum allowed" in error

    def test_min_datetime_naive_comparison(self):
        """min_datetime handles naive datetime comparison."""
        valid, error = validate_datetime("2025-10-13T14:30:00", min_datetime="2020-01-01T00:00:00Z")
        assert valid is True
        assert error is None

    # Date range tests - max_datetime
    def test_max_datetime_before_maximum(self):
        """Datetime before maximum passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", max_datetime="2030-12-31T23:59:59Z")
        assert valid is True
        assert error is None

    def test_max_datetime_equal_to_maximum(self):
        """Datetime equal to maximum passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", max_datetime="2025-10-13T14:30:00Z")
        assert valid is True
        assert error is None

    def test_max_datetime_after_maximum(self):
        """Datetime after maximum fails."""
        valid, error = validate_datetime("2030-12-31T23:59:59Z", max_datetime="2025-12-31T23:59:59Z")
        assert valid is False
        assert "is after maximum allowed" in error

    def test_max_datetime_naive_comparison(self):
        """max_datetime handles naive datetime comparison."""
        valid, error = validate_datetime("2025-10-13T14:30:00", max_datetime="2030-12-31T23:59:59Z")
        assert valid is True
        assert error is None

    def test_datetime_within_range(self):
        """Datetime within min and max range passes."""
        valid, error = validate_datetime(
            "2025-10-13T14:30:00Z", min_datetime="2020-01-01T00:00:00Z", max_datetime="2030-12-31T23:59:59Z"
        )
        assert valid is True
        assert error is None

    def test_datetime_outside_range_before_min(self):
        """Datetime before min fails."""
        valid, error = validate_datetime(
            "2019-12-31T23:59:59Z", min_datetime="2020-01-01T00:00:00Z", max_datetime="2030-12-31T23:59:59Z"
        )
        assert valid is False
        assert "is before minimum allowed" in error

    def test_datetime_outside_range_after_max(self):
        """Datetime after max fails."""
        valid, error = validate_datetime(
            "2031-01-01T00:00:00Z", min_datetime="2020-01-01T00:00:00Z", max_datetime="2030-12-31T23:59:59Z"
        )
        assert valid is False
        assert "is after maximum allowed" in error

    # Edge cases
    def test_invalid_min_datetime_format(self):
        """Invalid min_datetime format returns error."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", min_datetime="not-a-date")
        assert valid is False
        assert "Invalid min_datetime format" in error

    def test_invalid_max_datetime_format(self):
        """Invalid max_datetime format returns error."""
        valid, error = validate_datetime("2025-10-13T14:30:00Z", max_datetime="not-a-date")
        assert valid is False
        assert "Invalid max_datetime format" in error

    def test_datetime_with_microseconds(self):
        """Datetime with microseconds passes."""
        valid, error = validate_datetime("2025-10-13T14:30:00.123456Z")
        assert valid is True
        assert error is None

    def test_datetime_midnight(self):
        """Datetime at midnight passes."""
        valid, error = validate_datetime("2025-10-13T00:00:00Z")
        assert valid is True
        assert error is None

    def test_datetime_end_of_day(self):
        """Datetime at end of day passes."""
        valid, error = validate_datetime("2025-10-13T23:59:59Z")
        assert valid is True
        assert error is None

    def test_leap_year_feb_29(self):
        """Leap year Feb 29 passes."""
        valid, error = validate_datetime("2024-02-29T12:00:00Z")
        assert valid is True
        assert error is None

    def test_non_leap_year_feb_29(self):
        """Non-leap year Feb 29 fails."""
        valid, error = validate_datetime("2025-02-29T12:00:00Z")
        assert valid is False
        assert "does not match any accepted format" in error


class TestDateTimeValidationRule:
    """Tests for DateTimeValidationRule class."""

    def test_valid_datetime_passes(self):
        """Valid datetime passes validation rule."""
        rule = DateTimeValidationRule(formats=["ISO8601"])
        context = ValidationContext(
            name="SCHEDULED_TIME",
            raw_value="2025-10-13T14:30:00Z",
            coerced_value="2025-10-13T14:30:00Z",
            expected_type=str,
        )
        # Should not raise
        rule.validate(context)

    def test_invalid_datetime_raises_validation_error(self):
        """Invalid datetime raises ValidationError."""
        rule = DateTimeValidationRule(formats=["ISO8601"])
        context = ValidationContext(
            name="SCHEDULED_TIME",
            raw_value="not-a-date",
            coerced_value="not-a-date",
            expected_type=str,
        )
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)

        assert exc_info.value.variable_name == "SCHEDULED_TIME"
        assert "does not match any accepted format" in str(exc_info.value.reason)

    def test_custom_error_message(self):
        """Custom error message overrides default."""
        rule = DateTimeValidationRule(
            formats=["ISO8601"],
            error_message="Invalid timestamp format",
        )
        context = ValidationContext(
            name="TIMESTAMP",
            raw_value="not-a-date",
            coerced_value="not-a-date",
            expected_type=str,
        )
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)

        assert exc_info.value.reason == "Invalid timestamp format"

    def test_all_parameters(self):
        """All validation parameters work together."""
        rule = DateTimeValidationRule(
            formats=["ISO8601"],
            require_timezone=True,
            min_datetime="2020-01-01T00:00:00Z",
            max_datetime="2030-12-31T23:59:59Z",
        )

        # Valid datetime
        context = ValidationContext(
            name="EXPIRY_DATE",
            raw_value="2025-10-13T14:30:00Z",
            coerced_value="2025-10-13T14:30:00Z",
            expected_type=str,
        )
        rule.validate(context)  # Should not raise

        # No timezone
        context.raw_value = "2025-10-13T14:30:00"
        context.coerced_value = "2025-10-13T14:30:00"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "must include timezone information" in str(exc_info.value.reason)

        # Before min
        context.raw_value = "2019-01-01T00:00:00Z"
        context.coerced_value = "2019-01-01T00:00:00Z"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "is before minimum allowed" in str(exc_info.value.reason)

        # After max
        context.raw_value = "2031-01-01T00:00:00Z"
        context.coerced_value = "2031-01-01T00:00:00Z"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "is after maximum allowed" in str(exc_info.value.reason)

    def test_non_string_value_skipped(self):
        """Non-string values are skipped (not validated)."""
        rule = DateTimeValidationRule(formats=["ISO8601"])
        context = ValidationContext(
            name="PORT",
            raw_value="8080",
            coerced_value=8080,
            expected_type=int,
        )
        # Should not raise even though int is not a valid datetime
        rule.validate(context)

    def test_custom_format_validation(self):
        """Custom format validation works."""
        rule = DateTimeValidationRule(formats=["%Y-%m-%d"])
        context = ValidationContext(
            name="START_DATE",
            raw_value="2025-10-13",
            coerced_value="2025-10-13",
            expected_type=str,
        )
        rule.validate(context)  # Should not raise

        # Wrong format fails
        context.raw_value = "13/10/2025"
        context.coerced_value = "13/10/2025"
        with pytest.raises(ValidationError):
            rule.validate(context)

    def test_timezone_requirement_enforcement(self):
        """Timezone requirement is enforced."""
        rule = DateTimeValidationRule(require_timezone=True)

        # With timezone passes
        context = ValidationContext(
            name="TIMESTAMP",
            raw_value="2025-10-13T14:30:00Z",
            coerced_value="2025-10-13T14:30:00Z",
            expected_type=str,
        )
        rule.validate(context)

        # Without timezone fails
        context.raw_value = "2025-10-13T14:30:00"
        context.coerced_value = "2025-10-13T14:30:00"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "must include timezone information" in str(exc_info.value.reason)

    def test_real_world_expiration_date(self):
        """Real-world example: SSL certificate expiration validation."""
        rule = DateTimeValidationRule(
            formats=["ISO8601"],
            require_timezone=True,
            min_datetime="2025-01-01T00:00:00Z",  # Must be in future
            max_datetime="2027-12-31T23:59:59Z",  # Not too far in future
            error_message="SSL certificate expiration date must be between 2025-2027 with timezone",
        )

        # Valid expiration
        context = ValidationContext(
            name="CERT_EXPIRY",
            raw_value="2026-06-15T00:00:00Z",
            coerced_value="2026-06-15T00:00:00Z",
            expected_type=str,
        )
        rule.validate(context)

        # Expired certificate
        context.raw_value = "2024-01-01T00:00:00Z"
        context.coerced_value = "2024-01-01T00:00:00Z"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "SSL certificate expiration date" in str(exc_info.value.reason)

    def test_real_world_scheduled_task(self):
        """Real-world example: Scheduled task time validation."""
        # Time only
        rule = DateTimeValidationRule(formats=["%H:%M:%S"], error_message="Task schedule must be in HH:MM:SS format")

        # Valid schedule
        context = ValidationContext(
            name="BACKUP_TIME",
            raw_value="02:30:00",
            coerced_value="02:30:00",
            expected_type=str,
        )
        rule.validate(context)

        # Invalid format
        context.raw_value = "2:30 AM"
        context.coerced_value = "2:30 AM"
        with pytest.raises(ValidationError) as exc_info:
            rule.validate(context)
        assert "Task schedule must be in HH:MM:SS format" in str(exc_info.value.reason)

    def test_integration_with_validation_orchestrator(self):
        """DateTimeValidationRule works in ValidationOrchestrator."""
        from tripwire.core.validation_orchestrator import (
            LengthValidationRule,
            ValidationOrchestrator,
        )

        # Create orchestrator with multiple rules
        orchestrator = (
            ValidationOrchestrator()
            .add_rule(LengthValidationRule(min_length=10))
            .add_rule(DateTimeValidationRule(formats=["ISO8601"], require_timezone=True))
        )

        # Valid datetime passes both rules
        context = ValidationContext(
            name="SCHEDULED_TIME",
            raw_value="2025-10-13T14:30:00Z",
            coerced_value="2025-10-13T14:30:00Z",
            expected_type=str,
        )
        orchestrator.validate(context)

        # Too short fails first rule
        context.raw_value = "2025-10"
        context.coerced_value = "2025-10"
        with pytest.raises(ValidationError) as exc_info:
            orchestrator.validate(context)
        assert "too short" in str(exc_info.value.reason).lower()

        # No timezone fails second rule
        context.raw_value = "2025-10-13T14:30:00"
        context.coerced_value = "2025-10-13T14:30:00"
        with pytest.raises(ValidationError) as exc_info:
            orchestrator.validate(context)
        assert "must include timezone information" in str(exc_info.value.reason)
