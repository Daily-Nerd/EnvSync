"""Tests for core TripWire functionality."""

import os
from pathlib import Path

import pytest

from tripwire import TripWire, env
from tripwire.core.tripwire_v2 import TripWireV2
from tripwire.exceptions import MissingVariableError, TypeCoercionError, ValidationError


class TestTripWireInit:
    """Tests for TripWire initialization."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        instance = TripWire(auto_load=False)
        assert instance.env_file == Path(".env")
        assert instance.strict is False
        assert instance.detect_secrets is False

    def test_init_custom_file(self, tmp_path: Path) -> None:
        """Test initialization with custom env file."""
        env_file = tmp_path / ".env.custom"
        instance = TripWire(env_file=env_file, auto_load=False)
        assert instance.env_file == env_file

    def test_init_auto_load(self, sample_env_file: Path) -> None:
        """Test auto-loading of env file."""
        instance = TripWire(env_file=sample_env_file, auto_load=True)
        assert sample_env_file in instance._loaded_files


class TestRequireMethod:
    """Tests for require() method."""

    def test_require_existing_variable(self, sample_env_vars: dict[str, str]) -> None:
        """Test requiring an existing environment variable."""
        result = env.require("API_KEY")
        assert result == "test-api-key-12345"

    def test_require_missing_variable(self, isolated_env: None) -> None:
        """Test requiring a missing variable raises error."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        with pytest.raises(MissingVariableError, match="MISSING_VAR"):
            env_test.require("MISSING_VAR")

    def test_require_with_description(self, isolated_env: None) -> None:
        """Test error message includes description."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        with pytest.raises(
            MissingVariableError,
            match="Test description",
        ):
            env_test.require("MISSING_VAR", description="Test description")

    def test_require_with_default(self, isolated_env: None) -> None:
        """Test requiring variable with default value."""
        result = env.require("MISSING_VAR", default="default-value")
        assert result == "default-value"


class TestTypeCoercion:
    """Tests for type coercion."""

    def test_coerce_to_int(self, sample_env_vars: dict[str, str]) -> None:
        """Test integer type coercion."""
        result = env.require("PORT", type=int)
        assert result == 8000
        assert isinstance(result, int)

    def test_coerce_to_bool_true(self, sample_env_vars: dict[str, str]) -> None:
        """Test boolean type coercion for true values."""
        result = env.require("DEBUG", type=bool)
        assert result is True

    def test_coerce_to_bool_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test boolean type coercion for false values."""
        monkeypatch.setenv("DEBUG", "false")
        result = env.require("DEBUG", type=bool)
        assert result is False

    def test_coerce_to_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test list type coercion."""
        monkeypatch.setenv("HOSTS", "host1,host2,host3")
        result = env.require("HOSTS", type=list)
        assert result == ["host1", "host2", "host3"]

    def test_invalid_coercion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid type coercion raises error."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        monkeypatch.setenv("PORT", "not-a-number")
        with pytest.raises(TypeCoercionError):
            env_test.require("PORT", type=int)


class TestFormatValidation:
    """Tests for format validation."""

    def test_email_format_valid(self, sample_env_vars: dict[str, str]) -> None:
        """Test valid email format."""
        result = env.require("ADMIN_EMAIL", format="email")
        assert result == "admin@example.com"

    def test_email_format_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid email format raises error."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        monkeypatch.setenv("ADMIN_EMAIL", "not-an-email")
        with pytest.raises(ValidationError, match="Invalid format"):
            env_test.require("ADMIN_EMAIL", format="email")

    def test_url_format_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test valid URL format."""
        monkeypatch.setenv("API_URL", "https://api.example.com")
        result = env.require("API_URL", format="url")
        assert result == "https://api.example.com"

    def test_postgresql_format_valid(self, sample_env_vars: dict[str, str]) -> None:
        """Test valid PostgreSQL URL format."""
        result = env.require("DATABASE_URL", format="postgresql")
        assert result.startswith("postgresql://")


class TestPatternValidation:
    """Tests for pattern validation."""

    def test_pattern_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test matching pattern validation."""
        monkeypatch.setenv("API_KEY", "sk-1234567890abcdef")
        result = env.require("API_KEY", pattern=r"^sk-[a-z0-9]+$")
        assert result == "sk-1234567890abcdef"

    def test_pattern_mismatch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test non-matching pattern raises error."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        monkeypatch.setenv("API_KEY", "invalid-format")
        with pytest.raises(ValidationError, match="Does not match pattern"):
            env_test.require("API_KEY", pattern=r"^sk-[a-z0-9]+$")


class TestChoicesValidation:
    """Tests for choices validation."""

    def test_valid_choice(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test valid choice."""
        monkeypatch.setenv("ENV", "production")
        result = env.require(
            "ENV",
            choices=["development", "staging", "production"],
        )
        assert result == "production"

    def test_invalid_choice(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test invalid choice raises error."""
        # Use fail-fast mode for backward compatibility testing
        env_test = TripWireV2(collect_errors=False, auto_load=False)
        monkeypatch.setenv("ENV", "invalid")
        with pytest.raises(ValidationError, match="Not in allowed choices"):
            env_test.require(
                "ENV",
                choices=["development", "staging", "production"],
            )


class TestOptionalMethod:
    """Tests for optional() method."""

    def test_optional_with_value(self, sample_env_vars: dict[str, str]) -> None:
        """Test optional with existing value."""
        result = env.optional("DEBUG", default=False, type=bool)
        assert result is True

    def test_optional_without_value(self, isolated_env: None) -> None:
        """Test optional without value returns default."""
        result = env.optional("DEBUG", default=False, type=bool)
        assert result is False

    def test_optional_type_coercion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test optional with type coercion."""
        monkeypatch.setenv("TIMEOUT", "30")
        result = env.optional("TIMEOUT", default=10, type=int)
        assert result == 30
        assert isinstance(result, int)


class TestGetMethod:
    """Tests for get() method."""

    def test_get_existing(self, sample_env_vars: dict[str, str]) -> None:
        """Test getting existing variable."""
        result = env.get("API_KEY")
        assert result == "test-api-key-12345"

    def test_get_missing(self, isolated_env: None) -> None:
        """Test getting missing variable returns None."""
        result = env.get("MISSING_VAR")
        assert result is None

    def test_get_with_default(self, isolated_env: None) -> None:
        """Test getting missing variable with default."""
        result = env.get("MISSING_VAR", default="default")
        assert result == "default"


class TestHasMethod:
    """Tests for has() method."""

    def test_has_existing(self, sample_env_vars: dict[str, str]) -> None:
        """Test checking existing variable."""
        assert env.has("API_KEY") is True

    def test_has_missing(self, isolated_env: None) -> None:
        """Test checking missing variable."""
        assert env.has("MISSING_VAR") is False


class TestLoadMethod:
    """Tests for load() method."""

    def test_load_file(self, sample_env_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading env file."""
        # Clear any existing API_KEY that might be set by other tests
        monkeypatch.delenv("API_KEY", raising=False)

        instance = TripWire(auto_load=False)
        instance.load(sample_env_file)

        # Verify variables were loaded
        assert os.getenv("API_KEY") == "test-api-key-12345"

    def test_load_nonexistent_file_strict(self, tmp_path: Path) -> None:
        """Test loading nonexistent file in strict mode raises error."""
        from tripwire.exceptions import EnvFileNotFoundError

        instance = TripWire(auto_load=False, strict=True)
        with pytest.raises(EnvFileNotFoundError):
            instance.load(tmp_path / ".env.missing")

    def test_load_nonexistent_file_non_strict(self, tmp_path: Path) -> None:
        """Test loading nonexistent file in non-strict mode does nothing."""
        instance = TripWire(auto_load=False, strict=False)
        # Should not raise
        instance.load(tmp_path / ".env.missing")
