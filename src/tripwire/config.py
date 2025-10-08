"""Configuration file support for TripWire.

This module provides functionality to load and parse .tripwire.toml configuration files,
allowing teams to standardize environment variable requirements across projects.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class VariableConfig:
    """Configuration for a single environment variable.

    Attributes:
        name: Variable name
        required: Whether the variable is required
        type: Variable type (str, int, float, bool, list, dict)
        default: Default value if not set
        description: Human-readable description
        format: Built-in format validator
        pattern: Custom regex pattern
        choices: List of allowed values
        min_val: Minimum value for numeric types
        max_val: Maximum value for numeric types
        secret: Whether this is a secret value
    """

    name: str
    required: bool = True
    type: str = "str"
    default: Optional[Any] = None
    description: Optional[str] = None
    format: Optional[str] = None
    pattern: Optional[str] = None
    choices: Optional[List[str]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    secret: bool = False


@dataclass
class TripWireConfig:
    """TripWire project configuration.

    Attributes:
        variables: Dictionary of variable configurations
        env_file: Path to .env file (default: .env)
        strict: Whether to enable strict mode
        detect_secrets: Whether to detect potential secrets
        expand_vars: Whether to expand variable references
        allow_os_environ: Whether to allow fallback to os.environ
    """

    variables: Dict[str, VariableConfig] = field(default_factory=dict)
    env_file: str = ".env"
    strict: bool = False
    detect_secrets: bool = False
    expand_vars: bool = True
    allow_os_environ: bool = True


def load_config(config_path: Optional[Path] = None) -> Optional[TripWireConfig]:
    """Load TripWire configuration from .tripwire.toml file.

    Args:
        config_path: Path to config file (default: search for .tripwire.toml)

    Returns:
        TripWireConfig object or None if no config file found
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None or not config_path.exists():
        return None

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return None

    return parse_config(data)


def find_config_file(start_path: Optional[Path] = None) -> Optional[Path]:
    """Search for .tripwire.toml file in current directory and parents.

    Args:
        start_path: Directory to start search from (default: current directory)

    Returns:
        Path to config file or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search up to root
    while True:
        config_path = current / ".tripwire.toml"
        if config_path.exists():
            return config_path

        # Check if we've reached the root
        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def parse_config(data: Dict[str, Any]) -> TripWireConfig:
    """Parse configuration dictionary into TripWireConfig object.

    Args:
        data: Configuration dictionary from TOML file

    Returns:
        TripWireConfig object
    """
    config = TripWireConfig()

    # Parse global settings
    if "tripwire" in data:
        settings = data["tripwire"]
        config.env_file = settings.get("env_file", ".env")
        config.strict = settings.get("strict", False)
        config.detect_secrets = settings.get("detect_secrets", False)
        config.expand_vars = settings.get("expand_vars", True)
        config.allow_os_environ = settings.get("allow_os_environ", True)

    # Parse variable configurations
    if "variables" in data:
        for name, var_data in data["variables"].items():
            var_config = parse_variable_config(name, var_data)
            config.variables[name] = var_config

    return config


def parse_variable_config(name: str, data: Dict[str, Any]) -> VariableConfig:
    """Parse variable configuration from dictionary.

    Args:
        name: Variable name
        data: Variable configuration dictionary

    Returns:
        VariableConfig object
    """
    # Handle simple string format (description only)
    if isinstance(data, str):
        return VariableConfig(name=name, description=data)

    # Parse full configuration
    var_config = VariableConfig(name=name)

    # Basic settings
    var_config.required = data.get("required", True)
    var_config.type = data.get("type", "str")
    var_config.default = data.get("default")
    var_config.description = data.get("description")
    var_config.secret = data.get("secret", False)

    # Validation settings
    var_config.format = data.get("format")
    var_config.pattern = data.get("pattern")
    var_config.choices = data.get("choices")
    var_config.min_val = data.get("min")
    var_config.max_val = data.get("max")

    return var_config


def apply_config_to_tripwire(config: TripWireConfig, env_sync: Any) -> None:
    """Apply configuration settings to an TripWire instance.

    Args:
        config: Configuration to apply
        env_sync: TripWire instance to configure
    """
    env_sync.strict = config.strict
    env_sync.detect_secrets = config.detect_secrets


def validate_config(config: TripWireConfig) -> List[str]:
    """Validate configuration for common issues.

    Args:
        config: Configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: List[str] = []

    for name, var in config.variables.items():
        # Check type is valid
        valid_types = ["str", "int", "float", "bool", "list", "dict"]
        if var.type not in valid_types:
            errors.append(f"{name}: invalid type '{var.type}', must be one of {valid_types}")

        # Check format is valid if specified
        if var.format:
            valid_formats = ["email", "url", "uuid", "ipv4", "postgresql"]
            if var.format not in valid_formats:
                errors.append(f"{name}: invalid format '{var.format}', must be one of {valid_formats}")

        # Check min/max only used with numeric types
        if (var.min_val is not None or var.max_val is not None) and var.type not in [
            "int",
            "float",
        ]:
            errors.append(f"{name}: min/max can only be used with int or float types")

        # Check choices only used with string type
        if var.choices and var.type != "str":
            errors.append(f"{name}: choices can only be used with str type")

        # Check required variables don't have defaults
        if var.required and var.default is not None:
            errors.append(f"{name}: required variables should not have default values")

    return errors


def generate_example_config() -> str:
    """Generate an example .tripwire.toml configuration file.

    Returns:
        Example configuration as a string
    """
    return """# TripWire Configuration File
# This file defines environment variable requirements for your project

[tripwire]
# Path to .env file (default: .env)
env_file = ".env"

# Enable strict mode (warnings become errors)
strict = false

# Detect potential secrets in .env files
detect_secrets = true

# Expand variable references (${VAR} syntax)
expand_vars = true

# Allow fallback to os.environ when expanding variables
allow_os_environ = true

# Variable definitions
# Simple format: variable_name = "description"
# Full format: [variables.variable_name] with additional settings

[variables]
# Simple format examples
DATABASE_NAME = "Name of the database"
API_KEY = "API key for external service"

# Full format examples
[variables.DATABASE_URL]
required = true
type = "str"
description = "PostgreSQL database connection URL"
format = "postgresql"
secret = true

[variables.PORT]
required = false
type = "int"
default = 8000
description = "Server port number"
min = 1024
max = 65535

[variables.ENVIRONMENT]
required = true
type = "str"
description = "Deployment environment"
choices = ["development", "staging", "production"]

[variables.DEBUG]
required = false
type = "bool"
default = false
description = "Enable debug mode"

[variables.REDIS_HOST]
required = false
type = "str"
default = "localhost"
description = "Redis server hostname"

[variables.REDIS_PORT]
required = false
type = "int"
default = 6379
description = "Redis server port"

[variables.ALLOWED_HOSTS]
required = false
type = "list"
default = ["localhost", "127.0.0.1"]
description = "Comma-separated list of allowed hosts"

[variables.FEATURE_FLAGS]
required = false
type = "dict"
description = "JSON object with feature flags"
"""
