"""Tests for configuration file support."""

from pathlib import Path

import pytest

from tripwire.config import (
    TripWireConfig,
    VariableConfig,
    apply_config_to_tripwire,
    find_config_file,
    generate_example_config,
    load_config,
    parse_config,
    parse_variable_config,
    validate_config,
)


class TestVariableConfig:
    """Test VariableConfig dataclass."""

    def test_variable_config_defaults(self):
        """Test default values for VariableConfig."""
        config = VariableConfig(name="TEST_VAR")
        assert config.name == "TEST_VAR"
        assert config.required is True
        assert config.type == "str"
        assert config.default is None
        assert config.description is None
        assert config.secret is False

    def test_variable_config_full(self):
        """Test VariableConfig with all fields."""
        config = VariableConfig(
            name="PORT",
            required=False,
            type="int",
            default=8000,
            description="Server port",
            min_val=1024,
            max_val=65535,
        )
        assert config.name == "PORT"
        assert config.required is False
        assert config.type == "int"
        assert config.default == 8000
        assert config.description == "Server port"
        assert config.min_val == 1024
        assert config.max_val == 65535


class TestTripWireConfig:
    """Test TripWireConfig dataclass."""

    def test_tripwire_config_defaults(self):
        """Test default values for TripWireConfig."""
        config = TripWireConfig()
        assert config.env_file == ".env"
        assert config.strict is False
        assert config.detect_secrets is False
        assert config.expand_vars is True
        assert config.allow_os_environ is True
        assert len(config.variables) == 0


class TestParseVariableConfig:
    """Test parse_variable_config function."""

    def test_parse_simple_string(self):
        """Test parsing simple string description."""
        config = parse_variable_config("TEST_VAR", "A test variable")
        assert config.name == "TEST_VAR"
        assert config.description == "A test variable"
        assert config.required is True

    def test_parse_full_config(self):
        """Test parsing full variable configuration."""
        data = {
            "required": False,
            "type": "int",
            "default": 42,
            "description": "Answer to everything",
            "min": 0,
            "max": 100,
        }
        config = parse_variable_config("ANSWER", data)
        assert config.name == "ANSWER"
        assert config.required is False
        assert config.type == "int"
        assert config.default == 42
        assert config.description == "Answer to everything"
        assert config.min_val == 0
        assert config.max_val == 100

    def test_parse_with_format(self):
        """Test parsing with format validator."""
        data = {"format": "email", "description": "User email"}
        config = parse_variable_config("EMAIL", data)
        assert config.format == "email"
        assert config.description == "User email"

    def test_parse_with_pattern(self):
        """Test parsing with regex pattern."""
        data = {"pattern": r"^\d{3}-\d{3}-\d{4}$", "description": "Phone number"}
        config = parse_variable_config("PHONE", data)
        assert config.pattern == r"^\d{3}-\d{3}-\d{4}$"

    def test_parse_with_choices(self):
        """Test parsing with choices."""
        data = {"choices": ["dev", "staging", "prod"], "description": "Environment"}
        config = parse_variable_config("ENV", data)
        assert config.choices == ["dev", "staging", "prod"]

    def test_parse_secret(self):
        """Test parsing secret variable."""
        data = {"secret": True, "description": "API key"}
        config = parse_variable_config("API_KEY", data)
        assert config.secret is True


class TestParseConfig:
    """Test parse_config function."""

    def test_parse_empty_config(self):
        """Test parsing empty configuration."""
        config = parse_config({})
        assert isinstance(config, TripWireConfig)
        assert len(config.variables) == 0

    def test_parse_global_settings(self):
        """Test parsing global TripWire settings."""
        data = {
            "tripwire": {
                "env_file": ".env.production",
                "strict": True,
                "detect_secrets": True,
                "expand_vars": False,
                "allow_os_environ": False,
            }
        }
        config = parse_config(data)
        assert config.env_file == ".env.production"
        assert config.strict is True
        assert config.detect_secrets is True
        assert config.expand_vars is False
        assert config.allow_os_environ is False

    def test_parse_variables(self):
        """Test parsing variable configurations."""
        data = {
            "variables": {
                "DATABASE_URL": {
                    "required": True,
                    "type": "str",
                    "description": "Database connection URL",
                },
                "PORT": {"required": False, "type": "int", "default": 8000},
            }
        }
        config = parse_config(data)
        assert len(config.variables) == 2
        assert "DATABASE_URL" in config.variables
        assert "PORT" in config.variables

        db_var = config.variables["DATABASE_URL"]
        assert db_var.name == "DATABASE_URL"
        assert db_var.required is True
        assert db_var.type == "str"

        port_var = config.variables["PORT"]
        assert port_var.default == 8000

    def test_parse_variables_simple_format(self):
        """Test parsing variables with simple string format."""
        data = {"variables": {"API_KEY": "API key for external service"}}
        config = parse_config(data)
        assert len(config.variables) == 1
        api_var = config.variables["API_KEY"]
        assert api_var.description == "API key for external service"
        assert api_var.required is True


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_from_file(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text(
            """
[tripwire]
strict = true

[variables]
DATABASE_URL = "Database connection string"
"""
        )

        config = load_config(config_file)
        assert config is not None
        assert config.strict is True
        assert "DATABASE_URL" in config.variables

    def test_load_config_file_not_found(self, tmp_path):
        """Test loading configuration when file doesn't exist."""
        config = load_config(tmp_path / "nonexistent.toml")
        assert config is None

    def test_load_config_invalid_toml(self, tmp_path):
        """Test loading invalid TOML file."""
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text("invalid toml [[[")

        config = load_config(config_file)
        assert config is None

    def test_load_config_complex(self, tmp_path):
        """Test loading complex configuration."""
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text(
            """
[tripwire]
env_file = ".env.production"
strict = true
detect_secrets = true

[variables.DATABASE_URL]
required = true
type = "str"
description = "PostgreSQL connection URL"
format = "postgresql"
secret = true

[variables.PORT]
required = false
type = "int"
default = 8000
description = "Server port"
min = 1024
max = 65535

[variables.ENVIRONMENT]
required = true
type = "str"
choices = ["development", "staging", "production"]
description = "Deployment environment"
"""
        )

        config = load_config(config_file)
        assert config is not None
        assert config.env_file == ".env.production"
        assert config.strict is True
        assert config.detect_secrets is True

        assert len(config.variables) == 3

        db_var = config.variables["DATABASE_URL"]
        assert db_var.required is True
        assert db_var.format == "postgresql"
        assert db_var.secret is True

        port_var = config.variables["PORT"]
        assert port_var.type == "int"
        assert port_var.default == 8000
        assert port_var.min_val == 1024
        assert port_var.max_val == 65535

        env_var = config.variables["ENVIRONMENT"]
        assert env_var.choices == ["development", "staging", "production"]


class TestFindConfigFile:
    """Test find_config_file function."""

    def test_find_config_in_current_dir(self, tmp_path):
        """Test finding config file in current directory."""
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text("[tripwire]")

        found = find_config_file(tmp_path)
        assert found == config_file

    def test_find_config_in_parent_dir(self, tmp_path):
        """Test finding config file in parent directory."""
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text("[tripwire]")

        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)

        found = find_config_file(subdir)
        assert found == config_file

    def test_find_config_not_found(self, tmp_path):
        """Test when config file is not found."""
        found = find_config_file(tmp_path)
        assert found is None


class TestValidateConfig:
    """Test validate_config function."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", type="str")
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_invalid_type(self):
        """Test validation catches invalid type."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", type="invalid")
        errors = validate_config(config)
        assert len(errors) == 1
        assert "invalid type" in errors[0]

    def test_validate_invalid_format(self):
        """Test validation catches invalid format."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", format="invalid_format")
        errors = validate_config(config)
        assert len(errors) == 1
        assert "invalid format" in errors[0]

    def test_validate_min_max_on_non_numeric(self):
        """Test validation catches min/max on non-numeric types."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", type="str", min_val=0, max_val=10)
        errors = validate_config(config)
        assert len(errors) == 1
        assert "min/max can only be used with int or float" in errors[0]

    def test_validate_choices_on_non_string(self):
        """Test validation catches choices on non-string types."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", type="int", choices=["one", "two"])
        errors = validate_config(config)
        assert len(errors) == 1
        assert "choices can only be used with str" in errors[0]

    def test_validate_required_with_default(self):
        """Test validation catches required variables with defaults."""
        config = TripWireConfig()
        config.variables["TEST"] = VariableConfig(name="TEST", required=True, default="value")
        errors = validate_config(config)
        assert len(errors) == 1
        assert "required variables should not have default values" in errors[0]

    def test_validate_multiple_errors(self):
        """Test validation catches multiple errors."""
        config = TripWireConfig()
        config.variables["VAR1"] = VariableConfig(name="VAR1", type="invalid")
        config.variables["VAR2"] = VariableConfig(name="VAR2", format="bad_format")
        errors = validate_config(config)
        assert len(errors) == 2


class TestGenerateExampleConfig:
    """Test generate_example_config function."""

    def test_generate_example_config(self):
        """Test generating example configuration."""
        example = generate_example_config()
        assert isinstance(example, str)
        assert "[tripwire]" in example
        assert "[variables" in example
        assert "DATABASE_URL" in example
        assert "PORT" in example

    def test_example_config_is_valid_toml(self, tmp_path):
        """Test that generated example is valid TOML."""
        example = generate_example_config()
        config_file = tmp_path / ".tripwire.toml"
        config_file.write_text(example)

        # Should load successfully
        config = load_config(config_file)
        assert config is not None
        assert len(config.variables) > 0
