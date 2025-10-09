"""Comprehensive tests for schema validation functionality."""

import json
import tomllib
from pathlib import Path
from typing import Dict

import pytest
from click.testing import CliRunner

from tripwire.cli import main
from tripwire.schema import (
    TripWireSchema,
    VariableSchema,
    load_schema,
    validate_with_schema,
)


@pytest.fixture
def sample_schema_toml(tmp_path: Path) -> Path:
    """Create a sample .tripwire.toml file for testing."""
    # Using raw strings and proper TOML escaping
    schema_content = """# TripWire Test Schema
[project]
name = "test-project"
version = "1.0.0"
description = "Test project description"

[validation]
strict = true
allow_missing_optional = true
warn_unused = true

[security]
entropy_threshold = 4.5
scan_git_history = true
exclude_patterns = ["TEST_*"]

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
description = "PostgreSQL database connection"
secret = true
examples = ["postgresql://localhost:5432/dev"]

[variables.PORT]
type = "int"
required = false
default = 8000
min = 1024
max = 65535
description = "Server port"

[variables.DEBUG]
type = "bool"
required = false
default = false
description = "Enable debug mode"

[variables.API_KEY]
type = "string"
required = true
description = "API key for service"
secret = true
min_length = 10
max_length = 100

[variables.LOG_LEVEL]
type = "string"
required = false
default = "INFO"
choices = ["DEBUG", "INFO", "WARNING", "ERROR"]
description = "Logging level"

[variables.RATE_LIMIT]
type = "float"
required = false
default = 100.0
min = 1.0
max = 1000.0
description = "Requests per second"

[variables.EMAIL]
type = "string"
required = false
format = "email"
description = "Contact email address"

[variables.WEBSITE_URL]
type = "string"
required = false
format = "url"
description = "Website URL"

[variables.SERVER_ID]
type = "string"
required = false
format = "uuid"
description = "Server UUID"

[variables.SERVER_IP]
type = "string"
required = false
format = "ipv4"
description = "Server IP address"

[environments.development]
DATABASE_URL = "postgresql://localhost:5432/dev"
DEBUG = true
LOG_LEVEL = "DEBUG"

[environments.production]
DEBUG = false
LOG_LEVEL = "WARNING"
"""
    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)
    return schema_file


@pytest.fixture
def minimal_schema_toml(tmp_path: Path) -> Path:
    """Create a minimal .tripwire.toml file for testing."""
    schema_content = """[project]
name = "minimal"
version = "0.1.0"

[variables.API_KEY]
type = "string"
required = true
"""
    schema_file = tmp_path / ".tripwire.toml"
    schema_file.write_text(schema_content)
    return schema_file


# ============================================================================
# Schema Loading & Parsing Tests
# ============================================================================


class TestSchemaLoadingAndParsing:
    """Tests for schema loading and parsing from TOML files."""

    def test_load_schema_from_toml(self, sample_schema_toml: Path) -> None:
        """Test loading schema from TOML file."""
        schema = load_schema(sample_schema_toml)

        assert schema is not None
        assert schema.project_name == "test-project"
        assert schema.project_version == "1.0.0"
        assert schema.project_description == "Test project description"
        assert len(schema.variables) > 0

    def test_load_schema_missing_file(self, tmp_path: Path) -> None:
        """Test loading schema from non-existent file returns None."""
        missing_file = tmp_path / "nonexistent.toml"
        schema = load_schema(missing_file)

        assert schema is None

    def test_load_schema_invalid_toml(self, tmp_path: Path) -> None:
        """Test loading schema from malformed TOML raises error."""
        invalid_file = tmp_path / "invalid.toml"
        invalid_file.write_text("this is not valid [ toml")

        with pytest.raises(tomllib.TOMLDecodeError):
            TripWireSchema.from_toml(invalid_file)

    def test_schema_project_metadata(self, sample_schema_toml: Path) -> None:
        """Test parsing project metadata section."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        assert schema.project_name == "test-project"
        assert schema.project_version == "1.0.0"
        assert schema.project_description == "Test project description"

    def test_schema_validation_settings(self, sample_schema_toml: Path) -> None:
        """Test parsing validation settings section."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        assert schema.strict is True
        assert schema.allow_missing_optional is True
        assert schema.warn_unused is True

    def test_schema_security_settings(self, sample_schema_toml: Path) -> None:
        """Test parsing security settings section."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        assert schema.entropy_threshold == 4.5
        assert schema.scan_git_history is True
        assert "TEST_*" in schema.exclude_patterns


# ============================================================================
# Variable Schema Validation Tests
# ============================================================================


class TestVariableTypeValidation:
    """Tests for variable type validation."""

    def test_variable_type_validation_string(self) -> None:
        """Test string type validation."""
        var = VariableSchema(name="TEST", type="string")
        is_valid, error = var.validate("hello")

        assert is_valid is True
        assert error is None

    def test_variable_type_validation_int(self) -> None:
        """Test integer type validation with range."""
        var = VariableSchema(name="PORT", type="int", min=1024, max=65535)

        # Valid value
        is_valid, error = var.validate("8000")
        assert is_valid is True

        # Below min
        is_valid, error = var.validate("100")
        assert is_valid is False
        assert "Minimum value" in error

        # Above max
        is_valid, error = var.validate("70000")
        assert is_valid is False
        assert "Maximum value" in error

    def test_variable_type_validation_float(self) -> None:
        """Test float type validation with range."""
        var = VariableSchema(name="RATE", type="float", min=1.0, max=100.0)

        # Valid value
        is_valid, error = var.validate("50.5")
        assert is_valid is True

        # Below min
        is_valid, error = var.validate("0.5")
        assert is_valid is False

        # Above max
        is_valid, error = var.validate("150.0")
        assert is_valid is False

    def test_variable_type_validation_bool(self) -> None:
        """Test boolean type validation."""
        var = VariableSchema(name="DEBUG", type="bool")

        # Valid true values
        for value in ["true", "True", "1", "yes"]:
            is_valid, error = var.validate(value)
            assert is_valid is True

        # Valid false values
        for value in ["false", "False", "0", "no"]:
            is_valid, error = var.validate(value)
            assert is_valid is True

    def test_variable_type_validation_list(self) -> None:
        """Test list type validation and parsing."""
        var = VariableSchema(name="TAGS", type="list")

        # Comma-separated list
        is_valid, error = var.validate("a,b,c")
        assert is_valid is True

        # JSON array
        is_valid, error = var.validate('["x", "y", "z"]')
        assert is_valid is True

    def test_variable_type_validation_dict(self) -> None:
        """Test dict type validation and parsing."""
        var = VariableSchema(name="CONFIG", type="dict")

        # JSON object
        is_valid, error = var.validate('{"key": "value"}')
        assert is_valid is True

        # Invalid format
        is_valid, error = var.validate("not a dict")
        assert is_valid is False


class TestVariableFormatValidation:
    """Tests for format-based validation."""

    def test_variable_format_validation_email(self) -> None:
        """Test email format validation."""
        var = VariableSchema(name="EMAIL", type="string", format="email")

        # Valid email
        is_valid, error = var.validate("user@example.com")
        assert is_valid is True

        # Invalid email
        is_valid, error = var.validate("not-an-email")
        assert is_valid is False
        assert "Invalid format: email" in error

    def test_variable_format_validation_url(self) -> None:
        """Test URL format validation."""
        var = VariableSchema(name="URL", type="string", format="url")

        # Valid URL
        is_valid, error = var.validate("https://example.com")
        assert is_valid is True

        # Invalid URL
        is_valid, error = var.validate("not a url")
        assert is_valid is False

    def test_variable_format_validation_postgresql(self) -> None:
        """Test PostgreSQL URL format validation."""
        var = VariableSchema(name="DB", type="string", format="postgresql")

        # Valid PostgreSQL URL
        is_valid, error = var.validate("postgresql://localhost:5432/db")
        assert is_valid is True

        # Invalid URL
        is_valid, error = var.validate("mysql://localhost/db")
        assert is_valid is False

    def test_variable_format_validation_uuid(self) -> None:
        """Test UUID format validation."""
        var = VariableSchema(name="ID", type="string", format="uuid")

        # Valid UUID
        is_valid, error = var.validate("550e8400-e29b-41d4-a716-446655440000")
        assert is_valid is True

        # Invalid UUID
        is_valid, error = var.validate("not-a-uuid")
        assert is_valid is False

    def test_variable_format_validation_ipv4(self) -> None:
        """Test IPv4 format validation."""
        var = VariableSchema(name="IP", type="string", format="ipv4")

        # Valid IP
        is_valid, error = var.validate("192.168.1.1")
        assert is_valid is True

        # Invalid IP
        is_valid, error = var.validate("256.1.1.1")
        assert is_valid is False


class TestVariablePatternValidation:
    """Tests for pattern-based validation."""

    def test_variable_pattern_validation(self) -> None:
        """Test regex pattern validation."""
        var = VariableSchema(name="VERSION", type="string", pattern=r"^\d+\.\d+\.\d+$")

        # Valid pattern
        is_valid, error = var.validate("1.2.3")
        assert is_valid is True

        # Invalid pattern
        is_valid, error = var.validate("1.2")
        assert is_valid is False
        assert "Does not match pattern" in error


class TestVariableChoicesValidation:
    """Tests for choices/enum validation."""

    def test_variable_choices_validation(self) -> None:
        """Test choices validation."""
        var = VariableSchema(name="ENV", type="string", choices=["dev", "staging", "prod"])

        # Valid choice
        is_valid, error = var.validate("prod")
        assert is_valid is True

        # Invalid choice
        is_valid, error = var.validate("invalid")
        assert is_valid is False
        assert "Must be one of" in error


class TestVariableRangeValidation:
    """Tests for range validation on numeric types."""

    def test_variable_range_validation(self) -> None:
        """Test min/max range validation for int and float."""
        # Integer range
        int_var = VariableSchema(name="PORT", type="int", min=1, max=100)

        is_valid, _ = int_var.validate("50")
        assert is_valid is True

        is_valid, error = int_var.validate("0")
        assert is_valid is False
        assert "Minimum value is 1" in error

        is_valid, error = int_var.validate("200")
        assert is_valid is False
        assert "Maximum value is 100" in error

        # Float range
        float_var = VariableSchema(name="RATE", type="float", min=0.0, max=1.0)

        is_valid, _ = float_var.validate("0.5")
        assert is_valid is True

        is_valid, _ = float_var.validate("-0.1")
        assert is_valid is False

        is_valid, _ = float_var.validate("1.5")
        assert is_valid is False


class TestVariableLengthValidation:
    """Tests for string length validation."""

    def test_variable_length_validation(self) -> None:
        """Test min_length and max_length validation."""
        var = VariableSchema(name="PASSWORD", type="string", min_length=8, max_length=20)

        # Valid length
        is_valid, error = var.validate("password123")
        assert is_valid is True

        # Too short
        is_valid, error = var.validate("short")
        assert is_valid is False
        assert "Minimum length is 8" in error

        # Too long
        is_valid, error = var.validate("a" * 25)
        assert is_valid is False
        assert "Maximum length is 20" in error


# ============================================================================
# Environment-Specific Defaults Tests
# ============================================================================


class TestEnvironmentDefaults:
    """Tests for environment-specific default values."""

    def test_environment_defaults(self, sample_schema_toml: Path) -> None:
        """Test environment-specific default values."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        # Development environment
        dev_defaults = schema.get_defaults("development")
        assert dev_defaults["DATABASE_URL"] == "postgresql://localhost:5432/dev"
        assert dev_defaults["DEBUG"] is True
        assert dev_defaults["LOG_LEVEL"] == "DEBUG"

        # Production environment
        prod_defaults = schema.get_defaults("production")
        assert prod_defaults["DEBUG"] is False
        assert prod_defaults["LOG_LEVEL"] == "WARNING"

    def test_get_defaults_development(self, sample_schema_toml: Path) -> None:
        """Test getting defaults for development environment."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        defaults = schema.get_defaults("development")

        # Should include variable defaults
        assert defaults["PORT"] == 8000
        assert defaults["DEBUG"] is True  # Overridden by environment

        # Should include environment overrides
        assert "DATABASE_URL" in defaults
        assert "LOG_LEVEL" in defaults

    def test_get_defaults_production(self, sample_schema_toml: Path) -> None:
        """Test getting defaults for production environment."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        defaults = schema.get_defaults("production")

        assert defaults["DEBUG"] is False
        assert defaults["LOG_LEVEL"] == "WARNING"

    def test_get_defaults_missing_environment(self, sample_schema_toml: Path) -> None:
        """Test getting defaults for undefined environment uses base defaults."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        defaults = schema.get_defaults("staging")  # Not defined in schema

        # Should only have variable defaults, no environment overrides
        assert defaults["PORT"] == 8000
        assert defaults["DEBUG"] is False  # Base default
        assert "DATABASE_URL" not in defaults  # No environment override


# ============================================================================
# Schema Validation Against .env Tests
# ============================================================================


class TestSchemaValidationAgainstEnv:
    """Tests for validating .env files against schema."""

    def test_validate_env_all_valid(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test validation passes when all variables are valid."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        env_dict = {
            "DATABASE_URL": "postgresql://localhost:5432/test",
            "PORT": "8080",
            "DEBUG": "true",
            "API_KEY": "secret-key-1234567890",
            "LOG_LEVEL": "INFO",
        }

        is_valid, errors = schema.validate_env(env_dict)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_env_missing_required(self, sample_schema_toml: Path) -> None:
        """Test validation fails when required variables are missing."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        env_dict = {
            "PORT": "8080",
            "DEBUG": "true",
        }

        is_valid, errors = schema.validate_env(env_dict)

        assert is_valid is False
        # DATABASE_URL provided by development environment default, only API_KEY missing
        assert len(errors) == 1
        assert any("API_KEY" in err for err in errors)

    def test_validate_env_invalid_type(self, sample_schema_toml: Path) -> None:
        """Test validation fails on type mismatch."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        env_dict = {
            "DATABASE_URL": "postgresql://localhost:5432/test",
            "API_KEY": "secret-key-1234567890",
            "PORT": "not-a-number",  # Should be int
        }

        is_valid, errors = schema.validate_env(env_dict)

        assert is_valid is False
        assert any("PORT" in err for err in errors)

    def test_validate_env_invalid_format(self, sample_schema_toml: Path) -> None:
        """Test validation fails on format validation failure."""
        schema = TripWireSchema.from_toml(sample_schema_toml)

        env_dict = {
            "DATABASE_URL": "mysql://localhost:3306/test",  # Should be postgresql
            "API_KEY": "secret-key-1234567890",
        }

        is_valid, errors = schema.validate_env(env_dict)

        assert is_valid is False
        assert any("DATABASE_URL" in err and "Invalid format" in err for err in errors)

    def test_validate_env_strict_mode(self, sample_schema_toml: Path) -> None:
        """Test strict mode rejects unknown variables."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        schema.strict = True

        env_dict = {
            "DATABASE_URL": "postgresql://localhost:5432/test",
            "API_KEY": "secret-key-1234567890",
            "UNKNOWN_VAR": "some-value",  # Not in schema
        }

        is_valid, errors = schema.validate_env(env_dict)

        assert is_valid is False
        assert any("UNKNOWN_VAR" in err and "not in schema" in err for err in errors)

    def test_validate_env_permissive_mode(self, sample_schema_toml: Path) -> None:
        """Test permissive mode allows unknown variables."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        schema.strict = False

        env_dict = {
            "DATABASE_URL": "postgresql://localhost:5432/test",
            "API_KEY": "secret-key-1234567890",
            "UNKNOWN_VAR": "some-value",  # Not in schema
        }

        is_valid, errors = schema.validate_env(env_dict)

        # Should pass since strict=False allows unknown vars
        assert is_valid is True
        assert len(errors) == 0


# ============================================================================
# .env.example Generation Tests
# ============================================================================


class TestEnvExampleGeneration:
    """Tests for .env.example generation from schema."""

    def test_generate_env_example_basic(self, minimal_schema_toml: Path) -> None:
        """Test basic .env.example generation."""
        schema = TripWireSchema.from_toml(minimal_schema_toml)
        example = schema.generate_env_example()

        assert "# Environment Variables" in example
        assert "API_KEY=" in example

    def test_generate_env_example_with_defaults(self, sample_schema_toml: Path) -> None:
        """Test .env.example includes default values."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        example = schema.generate_env_example()

        # Optional vars should show defaults (Python's False becomes "False")
        assert "PORT=8000" in example
        assert "DEBUG=False" in example  # Python bool repr
        assert "LOG_LEVEL=INFO" in example

    def test_generate_env_example_with_examples(self, sample_schema_toml: Path) -> None:
        """Test .env.example includes example values."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        example = schema.generate_env_example()

        # DATABASE_URL has examples
        assert "postgresql://localhost:5432/dev" in example

    def test_generate_env_example_formatting(self, sample_schema_toml: Path) -> None:
        """Test .env.example has proper comments and formatting."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        example = schema.generate_env_example()

        # Should have sections
        assert "# Required Variables" in example
        assert "# Optional Variables" in example

        # Should have descriptions
        assert "PostgreSQL database connection" in example
        assert "Server port" in example

        # Should have type info
        assert "Type: int" in example
        assert "Type: string" in example


# ============================================================================
# CLI Commands Tests
# ============================================================================


class TestCLISchemaCommands:
    """Tests for schema-related CLI commands."""

    def test_cli_schema_init(self, tmp_path: Path) -> None:
        """Test 'schema init' command creates file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["schema", "init"])

            assert result.exit_code == 0
            assert Path(".tripwire.toml").exists()
            assert "Created .tripwire.toml" in result.output

    def test_cli_schema_init_overwrite(self, tmp_path: Path) -> None:
        """Test 'schema init' with overwrite protection."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial file
            runner.invoke(main, ["schema", "init"])

            # Try to create again without confirmation
            result = runner.invoke(main, ["schema", "init"], input="n\n")

            assert result.exit_code == 0
            assert "already exists" in result.output

    def test_cli_schema_validate_success(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test 'schema validate' command passes with valid .env."""
        runner = CliRunner()

        # Create valid .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """DATABASE_URL=postgresql://localhost:5432/test
API_KEY=secret-key-1234567890
PORT=8080
"""
        )

        result = runner.invoke(
            main,
            ["schema", "validate", "--env-file", str(env_file), "--schema-file", str(sample_schema_toml)],
        )

        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_cli_schema_validate_failure(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test 'schema validate' command fails with invalid .env."""
        runner = CliRunner()

        # Create invalid .env file (missing required vars)
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8080\n")

        result = runner.invoke(
            main,
            ["schema", "validate", "--env-file", str(env_file), "--schema-file", str(sample_schema_toml)],
        )

        # Should succeed but show errors (exit_code 0 without --strict)
        assert "Validation failed" in result.output
        # Development environment provides DATABASE_URL, so only API_KEY is missing
        assert "API_KEY" in result.output

    def test_cli_schema_validate_strict_flag(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test 'schema validate' --strict flag exits with error code."""
        runner = CliRunner()

        # Create invalid .env file
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8080\n")

        result = runner.invoke(
            main,
            [
                "schema",
                "validate",
                "--env-file",
                str(env_file),
                "--schema-file",
                str(sample_schema_toml),
                "--strict",
            ],
        )

        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_cli_schema_generate_example(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test 'schema generate-example' command creates file."""
        runner = CliRunner()

        output_file = tmp_path / ".env.example"

        result = runner.invoke(
            main,
            [
                "schema",
                "generate-example",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Generated" in result.output

        # Check content
        content = output_file.read_text()
        assert "DATABASE_URL=" in content
        assert "PORT=8000" in content

    def test_cli_schema_docs(self, sample_schema_toml: Path) -> None:
        """Test 'schema docs' command generates documentation."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["schema", "docs", "--schema-file", str(sample_schema_toml)],
        )

        assert result.exit_code == 0
        # Output should contain project name and variable info
        assert "test-project" in result.output or "Environment Variables" in result.output

    def test_cli_schema_validate_environment_flag(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test 'schema validate' --environment flag uses correct defaults."""
        runner = CliRunner()

        # Create minimal .env (required vars provided by environment defaults)
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret-key-1234567890\n")

        # Development environment provides DATABASE_URL default
        result = runner.invoke(
            main,
            [
                "schema",
                "validate",
                "--env-file",
                str(env_file),
                "--schema-file",
                str(sample_schema_toml),
                "--environment",
                "development",
            ],
        )

        assert result.exit_code == 0
        assert "development" in result.output.lower()

    def test_cli_schema_check_valid(self, sample_schema_toml: Path) -> None:
        """Test 'schema check' command with valid schema."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["schema", "check", "--schema-file", str(sample_schema_toml)],
        )

        assert result.exit_code == 0
        assert "Schema is valid" in result.output

    def test_cli_schema_check_invalid(self, tmp_path: Path) -> None:
        """Test 'schema check' command with invalid schema."""
        runner = CliRunner()

        # Create schema with no variables
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(
            """[project]
name = "test"
version = "1.0.0"
"""
        )

        result = runner.invoke(
            main,
            ["schema", "check", "--schema-file", str(schema_file)],
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "no variables defined" in result.output.lower()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestSchemaEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_schema(self, tmp_path: Path) -> None:
        """Test schema with no variables defined."""
        schema_content = """[project]
name = "empty"
version = "0.1.0"
"""
        schema_file = tmp_path / ".tripwire.toml"
        schema_file.write_text(schema_content)

        schema = TripWireSchema.from_toml(schema_file)
        assert len(schema.variables) == 0

        # Should validate successfully with empty env
        is_valid, errors = schema.validate_env({})
        assert is_valid is True

    def test_schema_with_no_environments(self, minimal_schema_toml: Path) -> None:
        """Test schema without environment-specific configs."""
        schema = TripWireSchema.from_toml(minimal_schema_toml)

        defaults = schema.get_defaults("production")
        assert defaults == {}  # No defaults defined

    def test_variable_with_all_validations(self) -> None:
        """Test variable with multiple validation rules."""
        var = VariableSchema(
            name="COMPLEX",
            type="string",
            required=True,
            format="email",
            min_length=5,
            max_length=100,
        )

        # Valid
        is_valid, _ = var.validate("user@example.com")
        assert is_valid is True

        # Invalid format (format validation runs before length validation)
        is_valid, error = var.validate("a@b.c")
        assert is_valid is False
        # Format validation fails first
        assert "Invalid format" in error

    def test_validate_with_schema_helper(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test validate_with_schema helper function."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """DATABASE_URL=postgresql://localhost:5432/test
API_KEY=secret-key-1234567890
"""
        )

        is_valid, errors = validate_with_schema(env_file, sample_schema_toml, "development")

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_with_schema_missing_schema(self, tmp_path: Path) -> None:
        """Test validate_with_schema with missing schema file."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST=value\n")

        is_valid, errors = validate_with_schema(env_file, tmp_path / "missing.toml", "development")

        assert is_valid is False
        assert len(errors) == 1
        assert "Schema file not found" in errors[0]
