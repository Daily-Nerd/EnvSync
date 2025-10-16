"""Comprehensive tests for TripWireV2 implementation.

This test suite ensures TripWireV2 meets the requirements specified in
TRIPWIREV2_DESIGN.md and maintains backward compatibility with the legacy implementation.
"""

import threading
from unittest.mock import MagicMock

import pytest

from tripwire import TripWire, TripWireV2
from tripwire.core.inference import FrameInspectionStrategy, TypeInferenceEngine
from tripwire.core.loader import DotenvFileSource, EnvFileLoader
from tripwire.core.registry import VariableMetadata, VariableRegistry
from tripwire.core.validation_orchestrator import (
    ValidationContext,
    ValidationOrchestrator,
)
from tripwire.exceptions import MissingVariableError, ValidationError


class TestBasicFunctionality:
    """Test basic TripWireV2 functionality."""

    def test_basic_require(self, monkeypatch):
        """Test simple require() call."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("PORT", "8000")

        PORT: int = env.require("PORT")

        assert PORT == 8000
        assert isinstance(PORT, int)

    def test_basic_optional(self, monkeypatch):
        """Test simple optional() call."""
        env = TripWireV2(auto_load=False)

        DEBUG: bool = env.optional("DEBUG", default=False)

        assert DEBUG is False
        assert isinstance(DEBUG, bool)

    def test_type_inference(self, monkeypatch):
        """Test type inference from annotations."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("PORT", "8000")

        # Type should be inferred as int from annotation
        PORT: int = env.require("PORT")

        assert PORT == 8000
        assert isinstance(PORT, int)

    def test_type_coercion_str_to_int(self, monkeypatch):
        """Test string to int coercion."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("COUNT", "42")

        COUNT: int = env.require("COUNT", type=int)

        assert COUNT == 42
        assert isinstance(COUNT, int)

    def test_type_coercion_str_to_bool(self, monkeypatch):
        """Test string to bool coercion."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("DEBUG", "true")

        DEBUG: bool = env.require("DEBUG", type=bool)

        assert DEBUG is True

    def test_type_coercion_str_to_float(self, monkeypatch):
        """Test string to float coercion."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("RATE", "3.14")

        RATE: float = env.require("RATE", type=float)

        assert RATE == 3.14
        assert isinstance(RATE, float)

    def test_type_coercion_str_to_list(self, monkeypatch):
        """Test string to list coercion."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("ITEMS", "a,b,c")

        ITEMS: list = env.require("ITEMS", type=list)

        assert ITEMS == ["a", "b", "c"]

    def test_type_coercion_str_to_dict(self, monkeypatch):
        """Test string to dict coercion."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("CONFIG", '{"key": "value"}')

        CONFIG: dict = env.require("CONFIG", type=dict)

        assert CONFIG == {"key": "value"}

    def test_missing_variable(self):
        """Test MissingVariableError raised when variable not found."""
        # Use collect_errors=False for legacy fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)

        with pytest.raises(MissingVariableError):
            env.require("NONEXISTENT")

    def test_default_value(self, monkeypatch):
        """Test default values work correctly."""
        env = TripWireV2(auto_load=False)

        # Ensure TIMEOUT doesn't exist (prevent pollution from other tests)
        monkeypatch.delenv("TIMEOUT", raising=False)

        # Variable doesn't exist, should return default
        TIMEOUT: int = env.require("TIMEOUT", default=30)

        assert TIMEOUT == 30

    def test_alias_tripwire_is_v2(self):
        """Test that TripWire is an alias for TripWireV2."""
        assert TripWire is TripWireV2


class TestValidation:
    """Test validation functionality."""

    def test_format_validation_email(self, monkeypatch):
        """Test email format validation."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("EMAIL", "test@example.com")

        EMAIL: str = env.require("EMAIL", format="email")

        assert EMAIL == "test@example.com"

    def test_format_validation_email_invalid(self, monkeypatch):
        """Test email format validation with invalid value."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("EMAIL", "invalid-email")

        with pytest.raises(ValidationError):
            env.require("EMAIL", format="email")

    def test_format_validation_url(self, monkeypatch):
        """Test URL format validation."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("URL", "https://example.com")

        URL: str = env.require("URL", format="url")

        assert URL == "https://example.com"

    def test_format_validation_postgresql(self, monkeypatch):
        """Test PostgreSQL format validation."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("DB", "postgresql://user:pass@localhost/db")

        DB: str = env.require("DB", format="postgresql")

        assert DB.startswith("postgresql://")

    def test_pattern_validation(self, monkeypatch):
        """Test regex pattern validation."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("CODE", "ABC123")

        CODE: str = env.require("CODE", pattern=r"^[A-Z]{3}\d{3}$")

        assert CODE == "ABC123"

    def test_pattern_validation_invalid(self, monkeypatch):
        """Test pattern validation with invalid value."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("CODE", "invalid")

        with pytest.raises(ValidationError):
            env.require("CODE", pattern=r"^[A-Z]{3}\d{3}$")

    def test_choices_validation(self, monkeypatch):
        """Test choices validation."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("ENV", "production")

        ENV: str = env.require("ENV", choices=["development", "staging", "production"])

        assert ENV == "production"

    def test_choices_validation_invalid(self, monkeypatch):
        """Test choices validation with invalid value."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("ENV", "invalid")

        with pytest.raises(ValidationError):
            env.require("ENV", choices=["development", "staging", "production"])

    def test_range_validation(self, monkeypatch):
        """Test range validation for numeric values."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("PORT", "8000")

        PORT: int = env.require("PORT", min_val=1, max_val=65535)

        assert PORT == 8000

    def test_range_validation_too_low(self, monkeypatch):
        """Test range validation with value too low."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("PORT", "0")

        with pytest.raises(ValidationError):
            env.require("PORT", type=int, min_val=1, max_val=65535)

    def test_range_validation_too_high(self, monkeypatch):
        """Test range validation with value too high."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("PORT", "99999")

        with pytest.raises(ValidationError):
            env.require("PORT", type=int, min_val=1, max_val=65535)

    def test_length_validation(self, monkeypatch):
        """Test length validation for strings."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("API_KEY", "abcdef12345")

        API_KEY: str = env.require("API_KEY", min_length=10, max_length=20)

        assert len(API_KEY) == 11

    def test_length_validation_too_short(self, monkeypatch):
        """Test length validation with string too short."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("API_KEY", "short")

        with pytest.raises(ValidationError):
            env.require("API_KEY", min_length=10)

    def test_length_validation_too_long(self, monkeypatch):
        """Test length validation with string too long."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("API_KEY", "a" * 100)

        with pytest.raises(ValidationError):
            env.require("API_KEY", max_length=20)

    def test_custom_validator(self, monkeypatch):
        """Test custom validation function."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("EMAIL", "test@company.com")

        def is_company_email(value: str) -> bool:
            return "@company.com" in value

        EMAIL: str = env.require("EMAIL", validator=is_company_email)

        assert EMAIL == "test@company.com"

    def test_custom_validator_fails(self, monkeypatch):
        """Test custom validator failure."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("EMAIL", "test@other.com")

        def is_company_email(value: str) -> bool:
            return "@company.com" in value

        with pytest.raises(ValidationError):
            env.require("EMAIL", validator=is_company_email)

    def test_multiple_validations(self, monkeypatch):
        """Test multiple validation rules in chain."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("EMAIL", "test@example.com")

        EMAIL: str = env.require("EMAIL", format="email", min_length=5, max_length=100, pattern=r".*@example\.com$")

        assert EMAIL == "test@example.com"


class TestDependencyInjection:
    """Test dependency injection capabilities."""

    def test_inject_custom_registry(self, monkeypatch):
        """Test injecting custom registry."""
        custom_registry = VariableRegistry()
        env = TripWireV2(registry=custom_registry, auto_load=False)

        monkeypatch.setenv("TEST", "value")
        result = env.require("TEST")

        # Verify registry was used
        metadata = custom_registry.get("TEST")
        assert metadata is not None
        assert metadata.name == "TEST"

    def test_inject_custom_loader(self, monkeypatch, tmp_path):
        """Test injecting custom loader."""
        # Create temp .env file
        env_file = tmp_path / ".env"
        env_file.write_text("CUSTOM_VAR=custom_value")

        # Create custom loader
        sources = [DotenvFileSource(env_file)]
        custom_loader = EnvFileLoader(sources, strict=False)

        env = TripWireV2(loader=custom_loader, auto_load=False)
        custom_loader.load_all()

        result = env.require("CUSTOM_VAR", default="default")
        assert result == "custom_value"

    def test_inject_custom_inference_engine(self, monkeypatch):
        """Test injecting custom inference engine."""
        # Create mock strategy that always returns int
        mock_strategy = MagicMock()
        mock_strategy.infer_type.return_value = int

        custom_engine = TypeInferenceEngine(mock_strategy)
        env = TripWireV2(inference_engine=custom_engine, auto_load=False)

        monkeypatch.setenv("TEST", "42")
        result = env.require("TEST")

        assert result == 42
        assert isinstance(result, int)

    def test_inject_all_components(self, monkeypatch):
        """Test injecting all components simultaneously."""
        custom_registry = VariableRegistry()
        mock_strategy = MagicMock()
        mock_strategy.infer_type.return_value = str
        custom_engine = TypeInferenceEngine(mock_strategy)
        custom_loader = EnvFileLoader([], strict=False)

        env = TripWireV2(
            registry=custom_registry, inference_engine=custom_engine, loader=custom_loader, auto_load=False
        )

        monkeypatch.setenv("TEST", "value")
        result = env.require("TEST")

        assert result == "value"
        assert custom_registry.get("TEST") is not None


class TestComponentInteraction:
    """Test interaction between components."""

    def test_registry_records_variables(self, monkeypatch):
        """Test that registry records all declared variables."""
        env = TripWireV2(auto_load=False)

        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")

        env.require("VAR1")
        env.require("VAR2")

        registry = env.get_registry()
        assert "VAR1" in registry
        assert "VAR2" in registry

    def test_loader_loads_files(self, tmp_path):
        """Test that loader successfully loads .env files."""
        env_file = tmp_path / ".env"
        env_file.write_text("LOADED_VAR=loaded_value")

        sources = [DotenvFileSource(env_file)]
        loader = EnvFileLoader(sources, strict=False)

        env = TripWireV2(loader=loader, auto_load=True)

        result = env.require("LOADED_VAR", default="default")
        assert result == "loaded_value"

    def test_inference_engine_infers_types(self, monkeypatch):
        """Test that inference engine correctly infers types."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("PORT", "8000")

        # Type should be inferred from annotation
        PORT: int = env.require("PORT")

        registry = env.get_registry()
        assert registry["PORT"]["type"] == "int"

    def test_validation_orchestrator_validates(self, monkeypatch):
        """Test that validation orchestrator executes rules."""
        # Use collect_errors=False for fail-fast behavior in tests
        env = TripWireV2(auto_load=False, collect_errors=False)
        monkeypatch.setenv("EMAIL", "invalid-email")

        # Should fail validation
        with pytest.raises(ValidationError):
            env.require("EMAIL", format="email")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy TripWire."""

    def test_api_compatible_with_legacy(self, monkeypatch):
        """Ensure API is compatible with legacy TripWire."""
        from tripwire import TripWireLegacy

        # Both should accept same parameters
        legacy_env = TripWireLegacy(auto_load=False)
        modern_env = TripWireV2(auto_load=False)

        monkeypatch.setenv("PORT", "8000")

        legacy_result = legacy_env.require("PORT", type=int)
        modern_result = modern_env.require("PORT", type=int)

        assert legacy_result == modern_result

    def test_module_level_env(self, monkeypatch):
        """Test that module-level env singleton works."""
        from tripwire import env as module_env

        monkeypatch.setenv("TEST_VAR", "test_value")

        result = module_env.require("TEST_VAR")
        assert result == "test_value"

    def test_get_registry_format(self, monkeypatch):
        """Test get_registry returns legacy-compatible format."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("TEST", "value")

        env.require("TEST")
        registry = env.get_registry()

        # Should have legacy format
        assert isinstance(registry, dict)
        assert "TEST" in registry
        assert "required" in registry["TEST"]
        assert "type" in registry["TEST"]
        assert "default" in registry["TEST"]


class TestThreadSafety:
    """Test thread safety of TripWireV2."""

    def test_concurrent_require_calls(self, monkeypatch):
        """Test concurrent require() calls don't cause race conditions."""
        env = TripWireV2(auto_load=False)

        for i in range(10):
            monkeypatch.setenv(f"VAR{i}", f"value{i}")

        results = []
        errors = []

        def worker(var_name: str):
            try:
                result = env.require(var_name)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"VAR{i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_concurrent_registry_access(self, monkeypatch):
        """Test concurrent registry access is thread-safe."""
        env = TripWireV2(auto_load=False)

        def worker(i: int):
            monkeypatch.setenv(f"VAR{i}", f"value{i}")
            env.require(f"VAR{i}")

        threads = []
        for i in range(20):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        registry = env.get_registry()
        # All variables should be registered without race conditions
        assert len(registry) >= 20


class TestLoadMethods:
    """Test file loading methods."""

    def test_load_method(self, tmp_path, monkeypatch):
        """Test load() method."""
        env_file = tmp_path / ".env"
        env_file.write_text("LOAD_TEST=loaded")

        env = TripWireV2(env_file=env_file, auto_load=False)
        env.load()

        result = env.require("LOAD_TEST", default="default")
        assert result == "loaded"

    def test_load_files_method(self, tmp_path):
        """Test load_files() method with multiple files."""
        env1 = tmp_path / ".env"
        env1.write_text("VAR1=value1\nVAR2=value2")

        env2 = tmp_path / ".env.local"
        env2.write_text("VAR2=overridden")

        env = TripWireV2(auto_load=False)
        env.load_files([env1, env2], override=True)

        var1 = env.require("VAR1", default="default1")
        var2 = env.require("VAR2", default="default2")

        assert var1 == "value1"
        assert var2 == "overridden"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string_value(self, monkeypatch):
        """Test handling of empty string values."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("EMPTY", "")

        result = env.require("EMPTY", default="default")
        assert result == ""

    def test_whitespace_value(self, monkeypatch):
        """Test handling of whitespace values."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("WHITESPACE", "   ")

        result = env.require("WHITESPACE")
        assert result == "   "

    def test_special_characters(self, monkeypatch):
        """Test handling of special characters."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("SPECIAL", "!@#$%^&*()")

        result = env.require("SPECIAL")
        assert result == "!@#$%^&*()"

    def test_unicode_characters(self, monkeypatch):
        """Test handling of unicode characters."""
        env = TripWireV2(auto_load=False)
        monkeypatch.setenv("UNICODE", "Hello 世界 🌍")

        result = env.require("UNICODE")
        assert result == "Hello 世界 🌍"
