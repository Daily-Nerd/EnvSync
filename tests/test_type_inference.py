"""Tests for type inference and typed convenience methods."""

import os
from pathlib import Path

import pytest

from tripwire import TripWire


class TestTypeInference:
    """Tests for automatic type inference from annotations."""

    def test_infer_int_type(self, tmp_path, monkeypatch):
        """Test inferring int type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        monkeypatch.delenv("PORT", raising=False)
        env = TripWire(env_file=str(env_file))

        # Type should be inferred from annotation
        PORT: int = env.require("PORT")

        assert isinstance(PORT, int)
        assert PORT == 8000

    def test_infer_bool_type(self, tmp_path, monkeypatch):
        """Test inferring bool type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("DEBUG_VAR=true\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DEBUG_VAR", raising=False)
        env = TripWire(env_file=str(env_file))

        DEBUG_VAR: bool = env.require("DEBUG_VAR")

        assert isinstance(DEBUG_VAR, bool)
        assert DEBUG_VAR is True

    def test_infer_float_type(self, tmp_path, monkeypatch):
        """Test inferring float type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("TIMEOUT=30.5\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("TIMEOUT", raising=False)
        env = TripWire(env_file=str(env_file))

        TIMEOUT: float = env.require("TIMEOUT")

        assert isinstance(TIMEOUT, float)
        assert TIMEOUT == 30.5

    def test_infer_str_type(self, tmp_path, monkeypatch):
        """Test inferring str type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("API_KEY", raising=False)
        env = TripWire(env_file=str(env_file))

        API_KEY: str = env.require("API_KEY")

        assert isinstance(API_KEY, str)
        assert API_KEY == "secret123"

    def test_infer_list_type(self, tmp_path, monkeypatch):
        """Test inferring list type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("ALLOWED_HOSTS=localhost,example.com\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
        env = TripWire(env_file=str(env_file))

        ALLOWED_HOSTS: list = env.require("ALLOWED_HOSTS")

        assert isinstance(ALLOWED_HOSTS, list)
        assert ALLOWED_HOSTS == ["localhost", "example.com"]

    def test_infer_dict_type(self, tmp_path, monkeypatch):
        """Test inferring dict type from annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text('CONFIG={"key": "value"}\n')

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CONFIG", raising=False)
        env = TripWire(env_file=str(env_file))

        CONFIG: dict = env.require("CONFIG")

        assert isinstance(CONFIG, dict)
        assert CONFIG == {"key": "value"}

    def test_explicit_type_overrides_annotation(self, tmp_path, monkeypatch):
        """Test that explicit type= parameter overrides annotation."""
        env_file = tmp_path / ".env"
        env_file.write_text("VALUE=42\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("VALUE", raising=False)
        env = TripWire(env_file=str(env_file))

        # Annotation says str, but type=int should win
        VALUE: str = env.require("VALUE", type=int)

        assert isinstance(VALUE, int)
        assert VALUE == 42

    def test_fallback_to_string_without_annotation(self, tmp_path, monkeypatch):
        """Test fallback to str when no annotation present."""
        env_file = tmp_path / ".env"
        env_file.write_text("FALLBACK_VALUE=hello\n")

        monkeypatch.chdir(tmp_path)
        env = TripWire(env_file=str(env_file))

        # No type annotation - should default to str
        result = env.require("FALLBACK_VALUE")

        assert isinstance(result, str)
        assert result == "hello"

    def test_type_inference_with_validation(self, tmp_path, monkeypatch):
        """Test type inference works with validation parameters."""
        env_file = tmp_path / ".env"
        env_file.write_text("VALIDATED_PORT=8080\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("VALIDATED_PORT", raising=False)
        env = TripWire(env_file=str(env_file))

        # Type inferred, validation applied
        VALIDATED_PORT: int = env.require("VALIDATED_PORT", min_val=1024, max_val=65535)

        assert isinstance(VALIDATED_PORT, int)
        assert VALIDATED_PORT == 8080

    def test_type_inference_with_optional(self, tmp_path, monkeypatch):
        """Test type inference works with optional method."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("OPT_DEBUG", raising=False)
        env = TripWire(env_file=str(env_file))

        # Type inferred from annotation
        OPT_DEBUG: bool = env.optional("OPT_DEBUG", default=False)

        assert isinstance(OPT_DEBUG, bool)
        assert OPT_DEBUG is False

    def test_type_inference_with_optional_existing_var(self, tmp_path, monkeypatch):
        """Test type inference with optional() when variable exists (regression test for frame depth bug)."""
        env_file = tmp_path / ".env"
        env_file.write_text("DEBUG_EXISTS=true\nPORT_EXISTS=8080\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("DEBUG_EXISTS", raising=False)
        monkeypatch.delenv("PORT_EXISTS", raising=False)
        env = TripWire(env_file=str(env_file))

        # This was broken before the frame depth fix - optional() would return string instead of bool
        DEBUG_EXISTS: bool = env.optional("DEBUG_EXISTS", default=False)
        PORT_EXISTS: int = env.optional("PORT_EXISTS", default=3000)

        assert isinstance(DEBUG_EXISTS, bool)
        assert DEBUG_EXISTS is True
        assert isinstance(PORT_EXISTS, int)
        assert PORT_EXISTS == 8080

    def test_type_inference_with_default(self, tmp_path, monkeypatch):
        """Test type inference with default value."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MAX_RETRIES", raising=False)
        env = TripWire(env_file=str(env_file))

        # Type inferred, default used
        MAX_RETRIES: int = env.require("MAX_RETRIES", default=3)

        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES == 3


class TestTypedConvenienceMethods:
    """Tests for typed convenience methods."""

    def test_require_int(self, tmp_path, monkeypatch):
        """Test require_int method."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PORT", raising=False)
        env = TripWire(env_file=str(env_file))

        port = env.require_int("PORT", min_val=1, max_val=65535)

        assert isinstance(port, int)
        assert port == 8000

    def test_require_int_with_validation(self, tmp_path, monkeypatch):
        """Test require_int with range validation."""
        env_file = tmp_path / ".env"
        env_file.write_text("LOW_PORT=100\n")

        monkeypatch.chdir(tmp_path)
        # Use fail-fast mode for clear validation testing
        env = TripWire(env_file=str(env_file), collect_errors=False)

        # Should fail validation
        with pytest.raises(Exception) as exc_info:
            env.require_int("LOW_PORT", min_val=1024, max_val=65535)

        assert "Out of range" in str(exc_info.value)

    def test_optional_int(self, tmp_path, monkeypatch):
        """Test optional_int method."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        env = TripWire(env_file=str(env_file))

        max_connections = env.optional_int("MAX_CONNECTIONS", default=100)

        assert isinstance(max_connections, int)
        assert max_connections == 100

    def test_require_bool(self, tmp_path, monkeypatch):
        """Test require_bool method."""
        env_file = tmp_path / ".env"
        env_file.write_text("ENABLE_FEATURE=yes\n")

        monkeypatch.chdir(tmp_path)
        env = TripWire(env_file=str(env_file))

        enable_feature = env.require_bool("ENABLE_FEATURE")

        assert isinstance(enable_feature, bool)
        assert enable_feature is True

    def test_optional_bool(self, tmp_path, monkeypatch):
        """Test optional_bool method."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid test pollution
        monkeypatch.delenv("DEBUG", raising=False)
        env = TripWire(env_file=str(env_file))

        debug = env.optional_bool("DEBUG", default=False)

        assert isinstance(debug, bool)
        assert debug is False

    def test_require_float(self, tmp_path, monkeypatch):
        """Test require_float method."""
        env_file = tmp_path / ".env"
        env_file.write_text("TIMEOUT=30.5\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution from project .env
        monkeypatch.delenv("TIMEOUT", raising=False)
        env = TripWire(env_file=str(env_file))

        timeout = env.require_float("TIMEOUT")

        assert isinstance(timeout, float)
        assert timeout == 30.5

    def test_optional_float(self, tmp_path, monkeypatch):
        """Test optional_float method."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        env = TripWire(env_file=str(env_file))

        rate_limit = env.optional_float("RATE_LIMIT", default=10.5)

        assert isinstance(rate_limit, float)
        assert rate_limit == 10.5

    def test_require_str(self, tmp_path, monkeypatch):
        """Test require_str method."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=sk-1234567890abcdef1234567890abcdef\n")

        monkeypatch.chdir(tmp_path)
        # Clear any existing API_KEY from environment
        monkeypatch.delenv("API_KEY", raising=False)
        env = TripWire(env_file=str(env_file))

        api_key = env.require_str("API_KEY", min_length=32)

        assert isinstance(api_key, str)
        assert len(api_key) >= 32

    def test_optional_str(self, tmp_path, monkeypatch):
        """Test optional_str method."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution from project .env
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        env = TripWire(env_file=str(env_file))

        log_level = env.optional_str("LOG_LEVEL", default="INFO")

        assert isinstance(log_level, str)
        assert log_level == "INFO"

    def test_typed_methods_in_dict(self, tmp_path, monkeypatch):
        """Test using typed methods in dictionary comprehension."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nDEBUG=true\nTIMEOUT=30.5\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        for key in ["PORT", "DEBUG", "TIMEOUT"]:
            monkeypatch.delenv(key, raising=False)
        env = TripWire(env_file=str(env_file))

        # Use typed methods in dictionary
        config = {
            "port": env.require_int("PORT", min_val=1, max_val=65535),
            "debug": env.optional_bool("DEBUG", default=False),
            "timeout": env.optional_float("TIMEOUT", default=30.0),
        }

        assert config["port"] == 8000
        assert config["debug"] is True
        assert config["timeout"] == 30.5


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility."""

    def test_old_api_with_type_parameter(self, tmp_path, monkeypatch):
        """Test that old code with type= parameter still works."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nDEBUG=true\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        for key in ["PORT", "DEBUG"]:
            monkeypatch.delenv(key, raising=False)
        env = TripWire(env_file=str(env_file))

        # Old style - should still work
        PORT: int = env.require("PORT", type=int, min_val=1, max_val=65535)
        DEBUG: bool = env.optional("DEBUG", default=False, type=bool)

        assert isinstance(PORT, int)
        assert isinstance(DEBUG, bool)
        assert PORT == 8000
        assert DEBUG is True

    def test_mixed_usage_inferred_and_explicit(self, tmp_path, monkeypatch):
        """Test mixing inferred types and explicit types."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nAPI_KEY=secret\nDEBUG=true\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        for key in ["PORT", "API_KEY", "DEBUG"]:
            monkeypatch.delenv(key, raising=False)
        env = TripWire(env_file=str(env_file))

        # Mix of inferred and explicit
        PORT: int = env.require("PORT", min_val=1)  # Inferred
        API_KEY: str = env.require("API_KEY", type=str)  # Explicit
        DEBUG: bool = env.require("DEBUG")  # Inferred

        assert PORT == 8000
        assert API_KEY == "secret"
        assert DEBUG is True

    def test_existing_validation_still_works(self, tmp_path, monkeypatch):
        """Test that all existing validation features work with type inference."""
        env_file = tmp_path / ".env"
        env_file.write_text("EMAIL=test@example.com\n" "URL=https://example.com\n" "ENV=production\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        for key in ["EMAIL", "URL", "ENV"]:
            monkeypatch.delenv(key, raising=False)
        env = TripWire(env_file=str(env_file))

        # Type inference with format validation
        EMAIL: str = env.require("EMAIL", format="email")
        URL: str = env.require("URL", format="url")
        ENV: str = env.require("ENV", choices=["development", "staging", "production"])

        assert EMAIL == "test@example.com"
        assert URL == "https://example.com"
        assert ENV == "production"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_inference_with_union_types(self, tmp_path, monkeypatch):
        """Test type inference with Optional[T] annotations."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PORT", raising=False)
        env = TripWire(env_file=str(env_file))

        from typing import Optional

        # Optional[int] should infer to int
        PORT: Optional[int] = env.require("PORT")

        assert isinstance(PORT, int)
        assert PORT == 8000

    def test_string_length_validation(self, tmp_path, monkeypatch):
        """Test string length validation."""
        env_file = tmp_path / ".env"
        env_file.write_text("SHORT=abc\nLONG=verylongstring\n")

        monkeypatch.chdir(tmp_path)
        # Use fail-fast mode for clear validation testing
        env = TripWire(env_file=str(env_file), collect_errors=False)

        # Min length validation
        with pytest.raises(Exception) as exc_info:
            env.require_str("SHORT", min_length=10)
        assert "too short" in str(exc_info.value).lower()

        # Max length validation
        with pytest.raises(Exception) as exc_info:
            env.require_str("LONG", max_length=5)
        assert "too long" in str(exc_info.value).lower()

        # Valid length
        API_KEY: str = env.require("LONG", min_length=5, max_length=20)
        assert API_KEY == "verylongstring"

    def test_typed_methods_with_missing_vars(self, tmp_path, monkeypatch):
        """Test typed methods with missing environment variables."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        # Use fail-fast mode for clear error testing
        env = TripWire(env_file=str(env_file), collect_errors=False)

        # Should raise MissingVariableError
        with pytest.raises(Exception) as exc_info:
            env.require_int("MISSING_PORT")

        assert "MISSING_PORT" in str(exc_info.value)

    def test_inference_without_source_code(self, tmp_path, monkeypatch):
        """Test that inference gracefully fails when source isn't available."""
        env_file = tmp_path / ".env"
        env_file.write_text("VALUE=test\n")

        monkeypatch.chdir(tmp_path)
        env = TripWire(env_file=str(env_file))

        # When executed without source file (like in REPL), should fallback to str
        # This is hard to test directly, but the fallback logic is there
        result = env.require("VALUE")
        assert isinstance(result, str)

    def test_type_coercion_errors_with_typed_methods(self, tmp_path, monkeypatch):
        """Test type coercion errors with typed methods."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=not_a_number\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        monkeypatch.delenv("PORT", raising=False)
        # Use fail-fast mode for clear error testing
        env = TripWire(env_file=str(env_file), collect_errors=False)

        # Should raise TypeCoercionError
        from tripwire.exceptions import TypeCoercionError

        with pytest.raises(TypeCoercionError) as exc_info:
            env.require_int("PORT")

        assert "PORT" in str(exc_info.value)

    def test_custom_validator_with_typed_methods(self, tmp_path, monkeypatch):
        """Test custom validators work with typed methods."""
        env_file = tmp_path / ".env"
        # Use port 2000 which is NOT privileged (>= 1024)
        env_file.write_text("PORT=2000\n")

        monkeypatch.chdir(tmp_path)
        # Clear environment to avoid pollution
        monkeypatch.delenv("PORT", raising=False)
        # Use fail-fast mode for clear validation testing
        env = TripWire(env_file=str(env_file), collect_errors=False)

        # Custom validator - requires privileged port (< 1024)
        def is_privileged_port(port: int) -> bool:
            return port < 1024

        # PORT=2000 should fail validation (not privileged)
        with pytest.raises(Exception):
            env.require_int("PORT", validator=is_privileged_port)

        # Should pass with privileged port
        env_file.write_text("PORT=80\n")
        env.load(env_file, override=True)

        port = env.require_int("PORT", validator=is_privileged_port)
        assert port == 80
