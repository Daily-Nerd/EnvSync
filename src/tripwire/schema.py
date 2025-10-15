"""
Configuration as Code - Schema validation for TripWire.

This module implements TOML-based schema validation for environment variables,
enabling declarative configuration management.
"""

import re
import tomllib  # Python 3.11+
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from tripwire.validation import (
    coerce_bool,
    coerce_dict,
    coerce_float,
    coerce_int,
    coerce_list,
)

# Phase 1 (v0.12.0): Custom validator prefix for deferred validation
CUSTOM_VALIDATOR_PREFIX = "custom:"


@dataclass
class VariableSchema:
    """Schema definition for a single environment variable."""

    name: str
    type: str = "string"
    required: bool = False
    default: Optional[Any] = None
    description: str = ""
    secret: bool = False
    examples: List[str] = field(default_factory=list)

    # Validation rules
    format: Optional[str] = None  # email, url, postgresql, uuid, ipv4
    pattern: Optional[str] = None  # regex pattern
    choices: Optional[List[str]] = None  # allowed values
    min: Optional[Union[int, float]] = None  # min value (for int/float)
    max: Optional[Union[int, float]] = None  # max value (for int/float)
    min_length: Optional[int] = None  # min string length
    max_length: Optional[int] = None  # max string length

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a value against this schema.

        Returns:
            (is_valid, error_message)
        """
        # Type validation
        if self.type == "string":
            if not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"

            # Format validation
            if self.format:
                if not self._validate_format(value):
                    return False, f"Invalid format: {self.format}"

            # Pattern validation
            if self.pattern and not re.match(self.pattern, value):
                return False, f"Does not match pattern: {self.pattern}"

            # Length validation
            if self.min_length and len(value) < self.min_length:
                return False, f"Minimum length is {self.min_length}"
            if self.max_length and len(value) > self.max_length:
                return False, f"Maximum length is {self.max_length}"

        elif self.type == "int":
            try:
                int_value = coerce_int(str(value))
            except (ValueError, TypeError) as e:
                return False, str(e)

            # Range validation
            if self.min is not None and int_value < self.min:
                return False, f"Minimum value is {self.min}"
            if self.max is not None and int_value > self.max:
                return False, f"Maximum value is {self.max}"

        elif self.type == "float":
            try:
                float_value = coerce_float(str(value))
            except (ValueError, TypeError) as e:
                return False, str(e)

            # Range validation
            if self.min is not None and float_value < self.min:
                return False, f"Minimum value is {self.min}"
            if self.max is not None and float_value > self.max:
                return False, f"Maximum value is {self.max}"

        elif self.type == "bool":
            try:
                coerce_bool(str(value))
            except (ValueError, TypeError) as e:
                return False, str(e)

        elif self.type == "list":
            try:
                coerce_list(str(value))
            except (ValueError, TypeError) as e:
                return False, str(e)

        elif self.type == "dict":
            try:
                coerce_dict(str(value))
            except (ValueError, TypeError) as e:
                return False, str(e)

        else:
            return False, f"Unknown type: {self.type}"

        # Choices validation
        if self.choices and value not in self.choices:
            return False, f"Must be one of: {', '.join(self.choices)}"

        return True, None

    def _validate_format(self, value: str) -> bool:
        """Validate string against format validator (includes custom validators).

        This method checks both built-in validators (email, url, postgresql, uuid, ipv4)
        and custom validators registered via register_validator().

        Special handling for custom validators (Phase 1 v0.12.0):
        - format="custom:*" skips validation (deferred to runtime)
        - Returns True to pass schema validation
        - Actual validation happens at application import-time when validators are registered
        - This solves the process boundary problem where CLI commands don't have
          access to custom validators registered in application code

        For custom validators to work, they must be imported/registered before
        validation runs (import-time registration).

        Returns:
            True if value matches format or is custom validator, False otherwise
        """
        from tripwire.validation import get_validator

        if not self.format:
            return False

        # Phase 1 (v0.12.0): Detect custom validator prefix
        # Skip validation for custom validators (not available in CLI context)
        if self.format.startswith(CUSTOM_VALIDATOR_PREFIX):
            # Defer validation to runtime when validators ARE registered
            return True

        # Use validator registry which includes both built-in and custom validators
        validator = get_validator(self.format)
        if not validator:
            return False

        # These validators return bool, not raise exceptions
        return validator(value)


@dataclass
class TripWireSchema:
    """Complete schema for TripWire configuration."""

    # Project metadata
    project_name: str = ""
    project_version: str = ""
    project_description: str = ""

    # Variable definitions
    variables: Dict[str, VariableSchema] = field(default_factory=dict)

    # Environment-specific overrides
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Validation settings
    strict: bool = True
    allow_missing_optional: bool = True
    warn_unused: bool = True

    # Security settings
    entropy_threshold: float = 4.5
    scan_git_history: bool = True
    exclude_patterns: List[str] = field(default_factory=list)

    @classmethod
    def from_toml(cls, toml_path: Union[str, Path]) -> "TripWireSchema":
        """Load schema from TOML file."""
        toml_path = Path(toml_path)

        if not toml_path.exists():
            raise FileNotFoundError(f"Schema file not found: {toml_path}")

        with open(toml_path, "rb") as f:
            data = tomllib.load(f)

        schema = cls()

        # Parse project metadata
        if "project" in data:
            project = data["project"]
            schema.project_name = project.get("name", "")
            schema.project_version = project.get("version", "")
            schema.project_description = project.get("description", "")

        # Parse validation settings
        if "validation" in data:
            validation = data["validation"]
            schema.strict = validation.get("strict", True)
            schema.allow_missing_optional = validation.get("allow_missing_optional", True)
            schema.warn_unused = validation.get("warn_unused", True)

        # Parse security settings
        if "security" in data:
            security = data["security"]
            schema.entropy_threshold = security.get("entropy_threshold", 4.5)
            schema.scan_git_history = security.get("scan_git_history", True)
            schema.exclude_patterns = security.get("exclude_patterns", [])

        # Parse variable definitions
        if "variables" in data:
            for var_name, var_config in data["variables"].items():
                schema.variables[var_name] = VariableSchema(
                    name=var_name,
                    type=var_config.get("type", "string"),
                    required=var_config.get("required", False),
                    default=var_config.get("default"),
                    description=var_config.get("description", ""),
                    secret=var_config.get("secret", False),
                    examples=var_config.get("examples", []),
                    format=var_config.get("format"),
                    pattern=var_config.get("pattern"),
                    choices=var_config.get("choices"),
                    min=var_config.get("min"),
                    max=var_config.get("max"),
                    min_length=var_config.get("min_length"),
                    max_length=var_config.get("max_length"),
                )

        # Parse environment overrides
        if "environments" in data:
            schema.environments = data["environments"]

        return schema

    def validate_env(self, env_dict: Dict[str, str], environment: str = "development") -> Tuple[bool, List[str]]:
        """
        Validate environment variables against schema.

        Args:
            env_dict: Dictionary of environment variables
            environment: Environment name (development, production, etc.)

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check required variables
        for var_name, var_schema in self.variables.items():
            if var_schema.required and var_name not in env_dict:
                # Check if environment provides default
                if environment in self.environments:
                    env_defaults = self.environments[environment]
                    if var_name in env_defaults:
                        continue  # Environment provides value

                errors.append(f"Required variable missing: {var_name}")

        # Validate present variables
        for var_name, value in env_dict.items():
            if var_name in self.variables:
                var_schema = self.variables[var_name]
                is_valid, error_msg = var_schema.validate(value)

                if not is_valid:
                    errors.append(f"{var_name}: {error_msg}")

            elif self.strict:
                errors.append(f"Unknown variable: {var_name} (not in schema)")

        return len(errors) == 0, errors

    def get_defaults(self, environment: str = "development") -> Dict[str, Any]:
        """Get default values for an environment."""
        defaults = {}

        # Variable defaults
        for var_name, var_schema in self.variables.items():
            if var_schema.default is not None:
                defaults[var_name] = var_schema.default

        # Environment-specific overrides
        if environment in self.environments:
            defaults.update(self.environments[environment])

        return defaults

    def generate_env_example(self) -> str:
        """Generate .env.example from schema."""
        lines = [
            "# Environment Variables",
            f"# Generated from .tripwire.toml",
            "",
        ]

        # Group by required/optional
        required_vars = [v for v in self.variables.values() if v.required]
        optional_vars = [v for v in self.variables.values() if not v.required]

        if required_vars:
            lines.append("# Required Variables")
            lines.append("")
            for var in required_vars:
                lines.extend(self._format_variable(var))
                lines.append("")

        if optional_vars:
            lines.append("# Optional Variables")
            lines.append("")
            for var in optional_vars:
                lines.extend(self._format_variable(var))
                lines.append("")

        return "\n".join(lines)

    def generate_env_for_environment(
        self,
        environment: str = "development",
        interactive: bool = False,
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Generate .env file for specific environment from schema.

        Args:
            environment: Environment name (development, production, etc.)
            interactive: If True, prompt for secret values

        Returns:
            Tuple of (generated .env file content, list of variables needing input)
        """
        from datetime import datetime

        lines = [
            f"# Environment: {environment}",
            f"# Generated from .tripwire.toml on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "# DO NOT COMMIT TO VERSION CONTROL",
            "",
        ]

        # Get environment-specific defaults
        env_defaults = self.get_defaults(environment)

        # Track variables needing manual input
        needs_input = []

        # Group by required/optional
        required_vars = sorted([v for v in self.variables.values() if v.required], key=lambda v: v.name)
        optional_vars = sorted([v for v in self.variables.values() if not v.required], key=lambda v: v.name)

        if required_vars:
            lines.append("# Required Variables")
            lines.append("")

            for var in required_vars:
                # Add description comment
                if var.description:
                    lines.append(f"# {var.description}")

                # Add metadata comment
                info_parts = [f"Type: {var.type}", "Required"]
                if var.format:
                    info_parts.append(f"Format: {var.format}")
                if var.secret:
                    info_parts.append("Secret: true")
                lines.append(f"# {' | '.join(info_parts)}")

                # Determine value
                value = None

                # Check environment-specific default first
                if var.name in env_defaults:
                    value = env_defaults[var.name]
                elif var.default is not None:
                    value = var.default

                # For secrets without defaults, use placeholder or prompt
                if value is None and var.secret:
                    if interactive:
                        # Will be prompted later
                        value = "PROMPT_ME"
                        needs_input.append((var.name, var.description or ""))
                    else:
                        value = "CHANGE_ME_SECRET_VALUE"
                        needs_input.append((var.name, var.description or ""))
                elif value is None:
                    # Required but not secret, use placeholder
                    value = ""
                    needs_input.append((var.name, var.description or ""))

                # Format value
                if isinstance(value, bool):
                    value = "true" if value else "false"

                lines.append(f"{var.name}={value}")
                lines.append("")

        if optional_vars:
            lines.append("# Optional Variables")
            lines.append("")

            for var in optional_vars:
                # Add description comment
                if var.description:
                    lines.append(f"# {var.description}")

                # Add metadata comment
                info_parts = [f"Type: {var.type}", "Optional"]
                if var.default is not None:
                    info_parts.append(f"Default: {var.default}")
                if var.format:
                    info_parts.append(f"Format: {var.format}")
                lines.append(f"# {' | '.join(info_parts)}")

                # Determine value
                value = None

                # Check environment-specific default first
                if var.name in env_defaults:
                    value = env_defaults[var.name]
                elif var.default is not None:
                    value = var.default
                else:
                    value = ""

                # Format value
                if isinstance(value, bool):
                    value = "true" if value else "false"

                lines.append(f"{var.name}={value}")
                lines.append("")

        return "\n".join(lines), needs_input

    def _format_variable(self, var: VariableSchema) -> List[str]:
        """Format a variable for .env.example."""
        lines = []

        # Description
        if var.description:
            lines.append(f"# {var.description}")

        # Type and validation info
        info_parts = [f"Type: {var.type}"]

        if var.required:
            info_parts.append("Required")
        else:
            info_parts.append("Optional")

        if var.default is not None:
            info_parts.append(f"Default: {var.default}")

        if var.format:
            info_parts.append(f"Format: {var.format}")

        if var.choices:
            info_parts.append(f"Choices: {', '.join(var.choices)}")

        if var.min is not None or var.max is not None:
            range_info = []
            if var.min is not None:
                range_info.append(f"min: {var.min}")
            if var.max is not None:
                range_info.append(f"max: {var.max}")
            info_parts.append(f"Range: {', '.join(range_info)}")

        lines.append(f"# {' | '.join(info_parts)}")

        # Examples
        if var.examples:
            lines.append(f"# Examples: {', '.join(str(e) for e in var.examples)}")

        # Variable line
        if var.default is not None:
            lines.append(f"{var.name}={var.default}")
        elif var.examples:
            lines.append(f"{var.name}={var.examples[0]}")
        else:
            lines.append(f"{var.name}=")

        return lines


def load_schema(schema_path: Union[str, Path] = ".tripwire.toml") -> Optional[TripWireSchema]:
    """
    Load TripWire schema from file.

    Args:
        schema_path: Path to .tripwire.toml file

    Returns:
        TripWireSchema or None if file doesn't exist
    """
    schema_path = Path(schema_path)

    if not schema_path.exists():
        return None

    return TripWireSchema.from_toml(schema_path)


def validate_with_schema(
    env_file: Union[str, Path] = ".env",
    schema_file: Union[str, Path] = ".tripwire.toml",
    environment: str = "development",
) -> Tuple[bool, List[str]]:
    """
    Validate .env file against schema.

    Args:
        env_file: Path to .env file
        schema_file: Path to .tripwire.toml schema
        environment: Environment name

    Returns:
        (is_valid, list_of_errors)
    """
    # Load schema
    schema = load_schema(schema_file)
    if not schema:
        return False, [f"Schema file not found: {schema_file}"]

    # Load .env file
    env_dict = {}
    env_path = Path(env_file)

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()

    # Validate
    return schema.validate_env(env_dict, environment)
