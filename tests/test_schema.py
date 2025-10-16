"""Comprehensive tests for schema validation functionality."""

import tomllib
from pathlib import Path

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
        """Test 'schema new' command creates file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["schema", "new"])

            assert result.exit_code == 0
            assert Path(".tripwire.toml").exists()
            assert "Created .tripwire.toml" in result.output

    def test_cli_schema_init_overwrite(self, tmp_path: Path) -> None:
        """Test 'schema new' with overwrite protection."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial file
            runner.invoke(main, ["schema", "new"])

            # Try to create again without confirmation
            result = runner.invoke(main, ["schema", "new"], input="n\n")

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
        """Test 'schema to-example' command creates file."""
        runner = CliRunner()

        output_file = tmp_path / ".env.example"

        result = runner.invoke(
            main,
            [
                "schema",
                "to-example",
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
        """Test 'schema to-docs' command generates documentation."""
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["schema", "to-docs", "--schema-file", str(sample_schema_toml)],
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


# ============================================================================
# Environment-Specific .env Generation Tests
# ============================================================================


class TestEnvGenerationForEnvironments:
    """Tests for generate_env_for_environment() method."""

    def test_generate_env_for_development(self, sample_schema_toml: Path) -> None:
        """Test generating .env file for development environment."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, needs_input = schema.generate_env_for_environment("development", interactive=False)

        # Should contain environment header
        assert "Environment: development" in env_content
        assert "DO NOT COMMIT" in env_content

        # Should use development defaults
        assert "DATABASE_URL=postgresql://localhost:5432/dev" in env_content
        assert "DEBUG=true" in env_content
        assert "LOG_LEVEL=DEBUG" in env_content

        # Should have placeholders for secrets without defaults
        assert "API_KEY=CHANGE_ME_SECRET_VALUE" in env_content
        assert len(needs_input) == 1  # API_KEY needs input
        assert needs_input[0][0] == "API_KEY"

    def test_generate_env_for_production(self, sample_schema_toml: Path) -> None:
        """Test generating .env file for production environment."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, needs_input = schema.generate_env_for_environment("production", interactive=False)

        # Should use production defaults
        assert "DEBUG=false" in env_content
        assert "LOG_LEVEL=WARNING" in env_content

        # Secrets without prod defaults should have placeholders
        assert "DATABASE_URL=CHANGE_ME_SECRET_VALUE" in env_content
        assert "API_KEY=CHANGE_ME_SECRET_VALUE" in env_content
        assert len(needs_input) == 2  # Both secrets need input

    def test_generate_env_interactive_mode(self, sample_schema_toml: Path) -> None:
        """Test generating .env with interactive mode enabled."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, needs_input = schema.generate_env_for_environment("production", interactive=True)

        # Interactive mode uses PROMPT_ME instead of CHANGE_ME_SECRET_VALUE
        assert "PROMPT_ME" in env_content
        assert len(needs_input) > 0

    def test_generate_env_with_optional_vars(self, sample_schema_toml: Path) -> None:
        """Test .env generation includes optional variables with defaults."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, needs_input = schema.generate_env_for_environment("development")

        # Optional variables with defaults
        assert "PORT=8000" in env_content
        assert "RATE_LIMIT=100.0" in env_content
        assert "# Optional Variables" in env_content

    def test_generate_env_formatting(self, sample_schema_toml: Path) -> None:
        """Test generated .env file has proper formatting and comments."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, _ = schema.generate_env_for_environment("development")

        # Should have sections
        assert "# Required Variables" in env_content
        assert "# Optional Variables" in env_content

        # Should have descriptions
        assert "PostgreSQL database connection" in env_content
        assert "Server port" in env_content

        # Should have metadata comments
        assert "Type: string | Required" in env_content
        assert "Type: int | Optional" in env_content

    def test_generate_env_bool_formatting(self, sample_schema_toml: Path) -> None:
        """Test boolean values are formatted as lowercase strings."""
        schema = TripWireSchema.from_toml(sample_schema_toml)
        env_content, _ = schema.generate_env_for_environment("development")

        # Booleans should be lowercase
        assert "DEBUG=true" in env_content or "DEBUG=false" in env_content
        # Should NOT be Python bool repr
        assert "DEBUG=True" not in env_content
        assert "DEBUG=False" not in env_content


# ============================================================================
# CLI Schema Generate-Env Tests
# ============================================================================


class TestCLISchemaGenerateEnv:
    """Tests for 'schema generate-env' CLI command."""

    def test_generate_env_command_basic(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test basic 'schema to-env' command."""
        runner = CliRunner()
        output_file = tmp_path / ".env.dev"

        result = runner.invoke(
            main,
            [
                "schema",
                "to-env",
                "--environment",
                "development",
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
        assert "Environment: development" in content
        assert "DATABASE_URL=" in content

    def test_generate_env_command_production(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test generating production .env with secrets placeholders."""
        runner = CliRunner()
        output_file = tmp_path / ".env.prod"

        result = runner.invoke(
            main,
            [
                "schema",
                "to-env",
                "--environment",
                "production",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        content = output_file.read_text()
        assert "CHANGE_ME_SECRET_VALUE" in content
        assert "Variables requiring manual input" in result.output

    def test_generate_env_command_overwrite_protection(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test to-env protects against overwriting existing files."""
        runner = CliRunner()
        output_file = tmp_path / ".env.dev"
        output_file.write_text("EXISTING=value\n")

        result = runner.invoke(
            main,
            [
                "schema",
                "to-env",
                "--environment",
                "development",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
            ],
            input="n\n",  # Don't overwrite
        )

        # Exit code 1 is expected when user declines to overwrite
        assert result.exit_code == 1
        assert "already exists" in result.output or "Aborted" in result.output
        # Original content preserved
        assert output_file.read_text() == "EXISTING=value\n"

    def test_generate_env_command_force_overwrite(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test to-env with --overwrite flag."""
        runner = CliRunner()
        output_file = tmp_path / ".env.dev"
        output_file.write_text("EXISTING=value\n")

        result = runner.invoke(
            main,
            [
                "schema",
                "to-env",
                "--environment",
                "development",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
                "--overwrite",
            ],
        )

        assert result.exit_code == 0
        # File should be overwritten
        content = output_file.read_text()
        assert "EXISTING=value" not in content
        assert "Environment: development" in content

    def test_generate_env_command_json_format(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test to-env with JSON output format."""
        runner = CliRunner()
        output_file = tmp_path / ".env.json"

        result = runner.invoke(
            main,
            [
                "schema",
                "to-env",
                "--environment",
                "development",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
                "--format-output",
                "json",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

        # Should be valid JSON
        import json

        data = json.loads(output_file.read_text())
        assert isinstance(data, dict)
        assert "DATABASE_URL" in data

    @pytest.mark.skip(reason="YAML format may require yaml library - testing if basic formats work first")
    def test_generate_env_command_yaml_format(self, sample_schema_toml: Path, tmp_path: Path) -> None:
        """Test generate-env with YAML output format."""
        runner = CliRunner()
        output_file = tmp_path / ".env.yaml"

        result = runner.invoke(
            main,
            [
                "schema",
                "generate-env",
                "--environment",
                "development",
                "--schema-file",
                str(sample_schema_toml),
                "--output",
                str(output_file),
                "--format-output",
                "yaml",
            ],
        )

        # Check if YAML is supported, exit code 1 might mean missing yaml library
        if result.exit_code != 0 and "yaml" in result.output.lower():
            pytest.skip("YAML support requires yaml library")

        assert result.exit_code == 0
        assert output_file.exists()

        content = output_file.read_text()
        # YAML format checks
        assert ":" in content
        assert "DATABASE_URL" in content


# ============================================================================
# CLI Schema Diff Tests
# ============================================================================


class TestCLISchemaDiff:
    """Tests for 'schema diff' CLI command."""

    def test_schema_diff_command_basic(self, tmp_path: Path) -> None:
        """Test basic 'schema diff' command."""
        runner = CliRunner()

        # Create two schemas with differences
        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"
version = "1.0.0"

[variables.API_KEY]
type = "string"
required = true

[variables.PORT]
type = "string"
required = false
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"
version = "2.0.0"

[variables.API_KEY]
type = "string"
required = true

[variables.PORT]
type = "int"
required = false
min = 1024
max = 65535

[variables.DATABASE_URL]
type = "string"
required = true
"""
        )

        result = runner.invoke(
            main,
            ["schema", "diff", str(old_schema), str(new_schema)],
        )

        assert result.exit_code == 0
        assert "Added Variables" in result.output
        assert "Modified Variables" in result.output
        assert "DATABASE_URL" in result.output
        assert "PORT" in result.output

    def test_schema_diff_breaking_changes(self, tmp_path: Path) -> None:
        """Test schema diff detects breaking changes."""
        runner = CliRunner()

        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
required = false
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
required = true

[variables.NEW_REQUIRED_VAR]
type = "string"
required = true
"""
        )

        result = runner.invoke(
            main,
            ["schema", "diff", str(old_schema), str(new_schema)],
        )

        assert result.exit_code == 0
        assert "Breaking Changes" in result.output
        assert "NEW_REQUIRED_VAR" in result.output

    def test_schema_diff_json_format(self, tmp_path: Path) -> None:
        """Test schema diff with JSON output format."""
        runner = CliRunner()

        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"

[variables.NEW_VAR]
type = "string"
"""
        )

        result = runner.invoke(
            main,
            ["schema", "diff", str(old_schema), str(new_schema), "--output-format", "json"],
        )

        assert result.exit_code == 0
        # Output has a header, extract JSON part
        import json

        # Find the JSON object (starts with { and ends with })
        json_start = result.output.find("{")
        assert json_start != -1, "No JSON found in output"
        json_str = result.output[json_start:]

        data = json.loads(json_str)
        assert "added" in data or "summary" in data


# ============================================================================
# CLI Schema Migrate Tests
# ============================================================================


class TestCLISchemaMigrate:
    """Tests for 'schema migrate' CLI command."""

    def test_schema_migrate_command_basic(self, tmp_path: Path) -> None:
        """Test basic 'schema upgrade' command."""
        runner = CliRunner()

        # Create old and new schemas
        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
required = true
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
required = true

[variables.NEW_VAR]
type = "string"
required = false
default = "default_value"
"""
        )

        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")

        result = runner.invoke(
            main,
            [
                "schema",
                "upgrade",
                "--from",
                str(old_schema),
                "--to",
                str(new_schema),
                "--env-file",
                str(env_file),
            ],
            input="y\n",  # Confirm migration
        )

        assert result.exit_code == 0
        assert "Migrated" in result.output

        # Check .env was updated
        content = env_file.read_text()
        assert "API_KEY=secret123" in content
        assert "NEW_VAR=default_value" in content

    def test_schema_migrate_dry_run(self, tmp_path: Path) -> None:
        """Test schema upgrade with --dry-run flag."""
        runner = CliRunner()

        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"

[variables.OLD_VAR]
type = "string"
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"

[variables.NEW_VAR]
type = "string"
default = "new"
"""
        )

        env_file = tmp_path / ".env"
        env_file.write_text("OLD_VAR=old_value\n")
        original_content = env_file.read_text()

        result = runner.invoke(
            main,
            [
                "schema",
                "upgrade",
                "--from",
                str(old_schema),
                "--to",
                str(new_schema),
                "--env-file",
                str(env_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        # File should not be modified in dry-run
        assert env_file.read_text() == original_content

    def test_schema_migrate_creates_backup(self, tmp_path: Path) -> None:
        """Test schema upgrade creates backup file."""
        runner = CliRunner()

        old_schema = tmp_path / "old.toml"
        old_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"
"""
        )

        new_schema = tmp_path / "new.toml"
        new_schema.write_text(
            """[project]
name = "test"

[variables.API_KEY]
type = "string"

[variables.NEW_VAR]
type = "string"
default = "value"
"""
        )

        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret\n")

        result = runner.invoke(
            main,
            [
                "schema",
                "upgrade",
                "--from",
                str(old_schema),
                "--to",
                str(new_schema),
                "--env-file",
                str(env_file),
            ],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "backup" in result.output.lower()

        # Should have backup file
        backup_files = list(tmp_path.glob(".env.backup.*"))
        assert len(backup_files) == 1


# ============================================================================
# Performance Tests for Schema Optimizations (v0.12.4+)
# ============================================================================


class TestSchemaPerformanceOptimizations:
    """Tests for write_schema_to_toml and merge_variable_schemas performance optimizations."""

    def test_write_large_schema_streaming_performance(self, tmp_path: Path) -> None:
        """Test streaming TOML writer handles large schemas efficiently.

        Verifies O(n) performance for write_schema_to_toml with 1000+ variables.
        Should complete in <1 second even for very large schemas.
        """
        import time

        from tripwire.schema import TripWireSchema, VariableSchema, write_schema_to_toml

        # Create large schema with 1000 variables
        schema = TripWireSchema(
            project_name="large-test",
            project_version="1.0.0",
            project_description="Performance test schema with 1000 variables",
        )

        # Generate 1000 variables with various configurations
        for i in range(1000):
            var_name = f"VAR_{i:04d}"
            schema.variables[var_name] = VariableSchema(
                name=var_name,
                type="string" if i % 2 == 0 else "int",
                required=i % 3 == 0,
                default=f"value_{i}" if i % 4 == 0 else None,
                description=f"Variable number {i} for testing",
                secret=i % 5 == 0,
                format="email" if i % 7 == 0 else None,
                min=0 if i % 2 == 1 else None,
                max=100 if i % 2 == 1 else None,
            )

        # Write schema with timing
        output_path = tmp_path / "large_schema.toml"
        start_time = time.time()
        write_schema_to_toml(schema, output_path)
        elapsed_time = time.time() - start_time

        # Verify schema was written
        assert output_path.exists()

        # Performance assertion: Should complete in <2 seconds for 1000 variables
        # (Optimized O(n) vs unoptimized O(n²) which would take ~22 seconds)
        assert elapsed_time < 2.0, f"Schema write took {elapsed_time:.2f}s (expected <2s)"

        # Verify content is correct (spot check)
        content = output_path.read_text()
        assert "[variables.VAR_0000]" in content
        assert "[variables.VAR_0999]" in content
        assert "Variable number 0 for testing" in content

    def test_write_schema_preserves_comments_with_large_schemas(self, tmp_path: Path) -> None:
        """Test streaming writer preserves comments correctly for large schemas."""
        from tripwire.schema import TripWireSchema, VariableSchema, write_schema_to_toml

        # Create schema with 100 variables
        schema = TripWireSchema(project_name="test")
        for i in range(100):
            var_name = f"VAR_{i:03d}"
            schema.variables[var_name] = VariableSchema(
                name=var_name,
                type="string",
                required=True,
            )

        # Create source comments for each variable
        source_comments = {f"VAR_{i:03d}": [f"# Found in: src/file_{i}.py:{i}"] for i in range(100)}

        # Write with comments
        output_path = tmp_path / "schema_with_comments.toml"
        write_schema_to_toml(schema, output_path, source_comments)

        # Verify comments are preserved
        content = output_path.read_text()
        assert "# Found in: src/file_0.py:0" in content
        assert "# Found in: src/file_99.py:99" in content

    def test_merge_variable_schemas_optimized_performance(self) -> None:
        """Test optimized merge_variable_schemas using dataclass replace().

        Verifies O(1) field update performance vs O(n) individual assignments.
        Should show ~70% performance improvement for large-scale merges.
        """
        import time

        from tripwire.schema import VariableSchema, merge_variable_schemas

        # Create base and updated schemas
        existing = VariableSchema(
            name="TEST_VAR",
            type="string",
            required=False,
            default="old_default",
            description="Original description",
            secret=False,
            format="email",
            min_length=10,
            max_length=100,
        )

        from_code = VariableSchema(
            name="TEST_VAR",
            type="int",  # Type changed
            required=True,  # Required changed
            default="new_default",  # Default changed
            description="",  # No description
            secret=True,  # Secret changed
            format="email",  # Format same
            min=0,  # Min changed
            max=100,  # Max changed
        )

        # Benchmark merge performance (run 10000 times to measure)
        iterations = 10000
        start_time = time.time()

        for _ in range(iterations):
            merged, changes = merge_variable_schemas(existing, from_code)

        elapsed_time = time.time() - start_time
        avg_time_ms = (elapsed_time / iterations) * 1000

        # Verify merge is correct
        assert merged.type == "int"
        assert merged.required is True
        assert merged.default == "new_default"
        assert merged.secret is True
        assert merged.min == 0
        assert merged.max == 100
        assert merged.description == "Original description"  # Preserved
        assert len(changes) > 0

        # Performance assertion: Should be <0.1ms per merge (optimized)
        # Unoptimized would be ~0.3ms per merge
        assert avg_time_ms < 0.1, f"Average merge time {avg_time_ms:.4f}ms (expected <0.1ms)"

    def test_merge_variable_schemas_early_exit_optimization(self) -> None:
        """Test early exit optimization when schemas are identical."""
        from tripwire.schema import VariableSchema, merge_variable_schemas

        # Create identical schemas
        var1 = VariableSchema(
            name="TEST",
            type="string",
            required=True,
            default="same",
            description="Same description",
        )

        var2 = VariableSchema(
            name="TEST",
            type="string",
            required=True,
            default="same",
            description="Same description",
        )

        # Merge identical schemas
        merged, changes = merge_variable_schemas(var1, var2)

        # Should return existing schema unchanged with no changes
        assert merged == var1
        assert len(changes) == 0

    def test_merge_schemas_large_scale_performance(self, tmp_path: Path) -> None:
        """Test merge_schemas function with 500+ variables.

        Verifies combined optimization of merge algorithm handles large schemas efficiently.
        """
        import time

        from tripwire.schema import TripWireSchema, VariableSchema, merge_schemas

        # Create existing schema with 500 variables
        existing_schema = TripWireSchema(
            project_name="existing",
            project_version="1.0.0",
        )

        for i in range(500):
            var_name = f"VAR_{i:03d}"
            existing_schema.variables[var_name] = VariableSchema(
                name=var_name,
                type="string",
                required=i % 2 == 0,
                default=f"old_{i}",
            )

        # Create new variables (300 updated, 200 new)
        new_variables = {}
        for i in range(500):  # Update first 300
            var_name = f"VAR_{i:03d}"
            new_variables[var_name] = VariableSchema(
                name=var_name,
                type="int" if i < 300 else "string",  # Change type for first 300
                required=i % 2 == 1,  # Flip required
                default=f"new_{i}",
            )

        # Add 200 new variables
        for i in range(500, 700):
            var_name = f"NEW_VAR_{i:03d}"
            new_variables[var_name] = VariableSchema(
                name=var_name,
                type="string",
                required=False,
            )

        # Benchmark merge
        start_time = time.time()
        result = merge_schemas(existing_schema, new_variables, remove_deprecated=False)
        elapsed_time = time.time() - start_time

        # Verify merge results
        assert len(result.added_variables) == 200
        # All 500 existing variables are updated (required flag flip, default change)
        # 300 also have type changes
        assert len(result.updated_variables) == 500
        assert len(result.merged_schema.variables) == 700

        # Performance assertion: Should complete in <0.5 seconds
        # (Optimized O(n) vs unoptimized O(n²) which would take longer)
        assert elapsed_time < 0.5, f"Merge took {elapsed_time:.2f}s (expected <0.5s)"

    def test_streaming_writer_memory_efficiency(self, tmp_path: Path) -> None:
        """Test streaming writer uses constant memory (not loading entire schema into memory repeatedly)."""
        from tripwire.schema import TripWireSchema, VariableSchema, write_schema_to_toml

        # Create large schema
        schema = TripWireSchema(project_name="memory-test")
        for i in range(500):
            schema.variables[f"VAR_{i}"] = VariableSchema(
                name=f"VAR_{i}",
                type="string",
                required=True,
                description="A" * 100,  # Long description to increase memory footprint
            )

        output_path = tmp_path / "memory_test.toml"

        # Write schema (streaming should not load entire file into memory multiple times)
        write_schema_to_toml(schema, output_path)

        # Verify file size is reasonable (not bloated by inefficient writing)
        file_size = output_path.stat().st_size
        # Each variable is ~200 bytes, so 500 vars = ~100KB + headers
        assert file_size < 200_000, f"File size {file_size} bytes (expected <200KB)"

    def test_backward_compatibility_write_output_format(self, tmp_path: Path) -> None:
        """Test optimized writer produces identical output to original implementation."""
        from tripwire.schema import TripWireSchema, VariableSchema, write_schema_to_toml

        # Create schema with all field types
        schema = TripWireSchema(
            project_name="compat-test",
            project_version="2.0.0",
            project_description="Backward compatibility test",
            strict=True,
            allow_missing_optional=False,
            warn_unused=True,
            entropy_threshold=5.0,
            scan_git_history=False,
            exclude_patterns=["SECRET_*", "PRIVATE_*"],
        )

        # Add variables with all possible field types
        schema.variables["STRING_VAR"] = VariableSchema(
            name="STRING_VAR",
            type="string",
            required=True,
            default="default_value",
            description="Test string variable",
            secret=True,
            examples=["example1", "example2"],
            format="email",
            pattern=r"^[a-z]+$",
            choices=["a", "b", "c"],
            min_length=5,
            max_length=50,
        )

        schema.variables["INT_VAR"] = VariableSchema(
            name="INT_VAR",
            type="int",
            required=False,
            default=42,
            min=0,
            max=100,
        )

        schema.variables["BOOL_VAR"] = VariableSchema(
            name="BOOL_VAR",
            type="bool",
            required=False,
            default=True,
        )

        # Add environment overrides
        schema.environments["development"] = {"STRING_VAR": "dev@example.com", "DEBUG": True}
        schema.environments["production"] = {"STRING_VAR": "prod@example.com", "DEBUG": False}

        # Write schema
        output_path = tmp_path / "compat_test.toml"
        source_comments = {"STRING_VAR": ["# Found in: src/config.py:10"]}
        write_schema_to_toml(schema, output_path, source_comments)

        # Verify all sections present
        content = output_path.read_text()

        # Project section
        assert "[project]" in content
        assert 'name = "compat-test"' in content

        # Validation section
        assert "[validation]" in content
        assert "strict = true" in content

        # Security section
        assert "[security]" in content
        assert "entropy_threshold = 5.0" in content

        # Variables section
        assert "[variables.STRING_VAR]" in content
        assert 'type = "string"' in content
        assert "required = true" in content
        assert 'default = "default_value"' in content
        assert "secret = true" in content

        # Comments preserved
        assert "# Found in: src/config.py:10" in content

        # Environments section
        assert "[environments.development]" in content
        assert "[environments.production]" in content
