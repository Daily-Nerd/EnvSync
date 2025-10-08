"""Tests for validation functions."""

import pytest

from tripwire.exceptions import TypeCoercionError
from tripwire.validation import (
    coerce_bool,
    coerce_dict,
    coerce_float,
    coerce_int,
    coerce_list,
    coerce_type,
    validate_choices,
    validate_email,
    validate_ipv4,
    validate_pattern,
    validate_postgresql_url,
    validate_range,
    validate_url,
    validate_uuid,
    validator,
)


class TestBooleanCoercion:
    """Tests for boolean type coercion."""

    @pytest.mark.parametrize(
        "value",
        ["true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"],
    )
    def test_coerce_bool_true(self, value: str) -> None:
        """Test various representations of true."""
        assert coerce_bool(value) is True

    @pytest.mark.parametrize(
        "value",
        ["false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF"],
    )
    def test_coerce_bool_false(self, value: str) -> None:
        """Test various representations of false."""
        assert coerce_bool(value) is False

    def test_coerce_bool_invalid(self) -> None:
        """Test invalid boolean value raises error."""
        with pytest.raises(ValueError, match="Cannot interpret"):
            coerce_bool("invalid")


class TestIntegerCoercion:
    """Tests for integer type coercion."""

    def test_coerce_int_valid(self) -> None:
        """Test valid integer conversion."""
        assert coerce_int("42") == 42
        assert coerce_int("-100") == -100
        assert coerce_int("0") == 0

    def test_coerce_int_invalid(self) -> None:
        """Test invalid integer conversion raises error."""
        with pytest.raises(ValueError):
            coerce_int("not a number")

    def test_coerce_int_float(self) -> None:
        """Test float string raises error for int conversion."""
        with pytest.raises(ValueError):
            coerce_int("3.14")


class TestFloatCoercion:
    """Tests for float type coercion."""

    def test_coerce_float_valid(self) -> None:
        """Test valid float conversion."""
        assert coerce_float("3.14") == 3.14
        assert coerce_float("-2.5") == -2.5
        assert coerce_float("42") == 42.0

    def test_coerce_float_invalid(self) -> None:
        """Test invalid float conversion raises error."""
        with pytest.raises(ValueError):
            coerce_float("not a number")


class TestListCoercion:
    """Tests for list type coercion."""

    def test_coerce_list_basic(self) -> None:
        """Test basic list conversion."""
        result = coerce_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_coerce_list_whitespace(self) -> None:
        """Test list conversion with whitespace."""
        result = coerce_list("a, b , c ")
        assert result == ["a", "b", "c"]

    def test_coerce_list_custom_delimiter(self) -> None:
        """Test list conversion with custom delimiter."""
        result = coerce_list("a|b|c", delimiter="|")
        assert result == ["a", "b", "c"]

    def test_coerce_list_empty(self) -> None:
        """Test empty list conversion."""
        result = coerce_list("")
        assert result == []


class TestDictCoercion:
    """Tests for dictionary type coercion."""

    def test_coerce_dict_valid(self) -> None:
        """Test valid JSON object conversion."""
        result = coerce_dict('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_coerce_dict_invalid_json(self) -> None:
        """Test invalid JSON raises error.

        The function first attempts to parse input as JSON. When JSON parsing fails,
        it falls back to key=value parsing. Since "not json" contains no "=" character,
        the key=value parser also fails, raising "Invalid key=value pair" error.
        """
        with pytest.raises(ValueError, match="Invalid key=value pair"):
            coerce_dict("not json")

    def test_coerce_dict_non_object(self) -> None:
        """Test non-object JSON (array) raises error.

        Arrays lack curly braces, triggering key=value parsing. Array string
        without "=" character fails with "Invalid key=value pair" error.
        """
        with pytest.raises(ValueError, match="Invalid key=value pair"):
            coerce_dict("[1, 2, 3]")


class TestCoerceType:
    """Tests for generic type coercion."""

    def test_coerce_to_string(self) -> None:
        """Test coercion to string (passthrough)."""
        result = coerce_type("test", str, "VAR")
        assert result == "test"
        assert isinstance(result, str)

    def test_coerce_to_int(self) -> None:
        """Test coercion to int."""
        result = coerce_type("42", int, "VAR")
        assert result == 42
        assert isinstance(result, int)

    def test_coerce_to_bool(self) -> None:
        """Test coercion to bool."""
        result = coerce_type("true", bool, "VAR")
        assert result is True

    def test_coerce_invalid_raises_typed_error(self) -> None:
        """Test invalid coercion raises TypeCoercionError."""
        with pytest.raises(TypeCoercionError) as exc_info:
            coerce_type("invalid", int, "PORT")

        assert exc_info.value.variable_name == "PORT"
        assert exc_info.value.target_type is int


class TestEmailValidation:
    """Tests for email validation."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "user_123@test-domain.com",
        ],
    )
    def test_valid_emails(self, email: str) -> None:
        """Test valid email formats."""
        assert validate_email(email) is True

    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
        ],
    )
    def test_invalid_emails(self, email: str) -> None:
        """Test invalid email formats."""
        assert validate_email(email) is False


class TestUrlValidation:
    """Tests for URL validation."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "https://sub.example.com/path",
            "https://example.com:8080/path?query=value",
        ],
    )
    def test_valid_urls(self, url: str) -> None:
        """Test valid URL formats."""
        assert validate_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "not a url",
            "ftp://example.com",  # Only http/https supported
            "//example.com",  # Missing protocol
        ],
    )
    def test_invalid_urls(self, url: str) -> None:
        """Test invalid URL formats."""
        assert validate_url(url) is False


class TestUuidValidation:
    """Tests for UUID validation."""

    def test_valid_uuid(self) -> None:
        """Test valid UUID format."""
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    @pytest.mark.parametrize(
        "uuid",
        [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400e29b41d4a716446655440000",  # No hyphens
        ],
    )
    def test_invalid_uuid(self, uuid: str) -> None:
        """Test invalid UUID formats."""
        assert validate_uuid(uuid) is False


class TestIpv4Validation:
    """Tests for IPv4 validation."""

    @pytest.mark.parametrize(
        "ip",
        [
            "192.168.1.1",
            "10.0.0.1",
            "255.255.255.255",
            "0.0.0.0",
        ],
    )
    def test_valid_ipv4(self, ip: str) -> None:
        """Test valid IPv4 addresses."""
        assert validate_ipv4(ip) is True

    @pytest.mark.parametrize(
        "ip",
        [
            "256.1.1.1",  # Octet > 255
            "192.168.1",  # Too few octets
            "192.168.1.1.1",  # Too many octets
            "not.an.ip.address",  # Non-numeric
        ],
    )
    def test_invalid_ipv4(self, ip: str) -> None:
        """Test invalid IPv4 addresses."""
        assert validate_ipv4(ip) is False


class TestPostgresqlUrlValidation:
    """Tests for PostgreSQL URL validation."""

    @pytest.mark.parametrize(
        "url",
        [
            "postgresql://localhost/mydb",
            "postgres://user:pass@host:5432/db",
            "postgresql://user@host/database",
        ],
    )
    def test_valid_postgresql_url(self, url: str) -> None:
        """Test valid PostgreSQL URLs."""
        assert validate_postgresql_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "mysql://localhost/mydb",  # Wrong protocol
            "http://localhost/mydb",  # Wrong protocol
            "not a url",
        ],
    )
    def test_invalid_postgresql_url(self, url: str) -> None:
        """Test invalid PostgreSQL URLs."""
        assert validate_postgresql_url(url) is False


class TestPatternValidation:
    """Tests for pattern validation."""

    def test_validate_pattern_match(self) -> None:
        """Test matching pattern."""
        assert validate_pattern("abc123", r"^[a-z]+\d+$") is True

    def test_validate_pattern_no_match(self) -> None:
        """Test non-matching pattern."""
        assert validate_pattern("ABC123", r"^[a-z]+\d+$") is False


class TestRangeValidation:
    """Tests for range validation."""

    def test_range_within(self) -> None:
        """Test value within range."""
        assert validate_range(50, 0, 100) is True

    def test_range_boundaries(self) -> None:
        """Test boundary values."""
        assert validate_range(0, 0, 100) is True
        assert validate_range(100, 0, 100) is True

    def test_range_below_min(self) -> None:
        """Test value below minimum."""
        assert validate_range(-1, 0, 100) is False

    def test_range_above_max(self) -> None:
        """Test value above maximum."""
        assert validate_range(101, 0, 100) is False

    def test_range_no_min(self) -> None:
        """Test range with no minimum."""
        assert validate_range(-999, None, 100) is True

    def test_range_no_max(self) -> None:
        """Test range with no maximum."""
        assert validate_range(999, 0, None) is True


class TestChoicesValidation:
    """Tests for choices validation."""

    def test_valid_choice(self) -> None:
        """Test valid choice."""
        assert validate_choices("production", ["dev", "staging", "production"]) is True

    def test_invalid_choice(self) -> None:
        """Test invalid choice."""
        assert validate_choices("invalid", ["dev", "staging", "production"]) is False


class TestValidatorDecorator:
    """Tests for validator decorator."""

    def test_validator_decorator(self) -> None:
        """Test validator decorator."""

        @validator
        def custom_validator(value: str) -> bool:
            return len(value) > 5

        assert callable(custom_validator)
        assert custom_validator("longvalue") is True
        assert custom_validator("short") is False
