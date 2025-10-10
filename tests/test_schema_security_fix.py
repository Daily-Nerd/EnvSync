"""Test security fix: secrets should never have defaults in schema files (v0.7.1)."""

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from tripwire.cli import main


class TestSchemaSecurityFix:
    """Tests for v0.7.1 security fix: secrets must not have defaults in schema."""

    def test_schema_from_example_excludes_secret_defaults(self, tmp_path: Path) -> None:
        """Test that 'schema from-example' never includes defaults for secrets.

        Security rationale:
        - .tripwire.toml is committed to git (version controlled)
        - Secrets should only exist in .env files (never committed)
        - Having defaults for secrets risks accidental exposure
        """
        runner = CliRunner()

        # Create .env.example with secret that has a value (simulating a placeholder)
        env_example = tmp_path / ".env.example"
        env_example.write_text(
            """# API Configuration
API_KEY=your-api-key-here
SECRET_TOKEN=sk-test-placeholder
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE

# Non-secret with default
PORT=8000
DEBUG=true
"""
        )

        output_schema = tmp_path / ".tripwire.toml"

        # Run schema from-example command
        result = runner.invoke(
            main,
            [
                "schema",
                "from-example",
                "--source",
                str(env_example),
                "--output",
                str(output_schema),
            ],
        )

        assert result.exit_code == 0
        assert output_schema.exists()

        # Load the generated schema
        with open(output_schema, "rb") as f:
            schema_data = tomllib.load(f)

        # Verify secrets are detected
        assert "variables" in schema_data
        api_key_var = schema_data["variables"]["API_KEY"]
        secret_token_var = schema_data["variables"]["SECRET_TOKEN"]
        aws_key_var = schema_data["variables"]["AWS_ACCESS_KEY"]

        # Secrets should be marked as secret=true
        assert api_key_var.get("secret") is True
        assert secret_token_var.get("secret") is True
        assert aws_key_var.get("secret") is True

        # CRITICAL: Secrets should NOT have defaults
        assert "default" not in api_key_var, "API_KEY should not have default value (security risk)"
        assert "default" not in secret_token_var, "SECRET_TOKEN should not have default value (security risk)"
        assert "default" not in aws_key_var, "AWS_ACCESS_KEY should not have default value (security risk)"

        # Non-secrets should still have defaults
        port_var = schema_data["variables"]["PORT"]
        debug_var = schema_data["variables"]["DEBUG"]
        assert "default" in port_var
        assert port_var["default"] == 8000
        assert "default" in debug_var
        assert debug_var["default"] is True

    def test_schema_from_example_output_message(self, tmp_path: Path) -> None:
        """Test that output message clarifies security behavior for secrets."""
        runner = CliRunner()

        env_example = tmp_path / ".env.example"
        # Use values that will be detected as secrets by the secret scanner
        env_example.write_text(
            """API_KEY=xxsk-1234567890abcdef1234567890abcdef
DATABASE_PASSWORD=SuperSecret123!Password
JWT_SECRET=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
PORT=8000
"""
        )

        output_schema = tmp_path / ".tripwire.toml"

        result = runner.invoke(
            main,
            [
                "schema",
                "from-example",
                "--source",
                str(env_example),
                "--output",
                str(output_schema),
            ],
        )

        assert result.exit_code == 0

        # Output should mention secrets and security behavior
        assert "secret(s)" in result.output
        assert "secrets have no defaults for security" in result.output

    def test_schema_check_warns_about_secrets_with_defaults(self, tmp_path: Path) -> None:
        """Test that 'schema check' warns about secrets with defaults (bad practice)."""
        runner = CliRunner()

        # Create a schema with a secret that has a default (bad!)
        bad_schema = tmp_path / ".tripwire.toml"
        bad_schema.write_text(
            """[project]
name = "test"
version = "1.0.0"

[variables.API_KEY]
type = "string"
required = true
secret = true
default = "sk-test-12345"  # BAD: Secret should not have default

[variables.PORT]
type = "int"
default = 8000
"""
        )

        result = runner.invoke(
            main,
            ["schema", "check", "--schema-file", str(bad_schema)],
        )

        # Should pass validation but show warning
        assert result.exit_code == 0  # Warnings don't fail validation
        assert "warning" in result.output.lower()
        assert "API_KEY" in result.output
        assert "Secret has default value" in result.output
        assert "security risk" in result.output

    def test_schema_from_real_env_excludes_all_secret_defaults(self, tmp_path: Path) -> None:
        """Test that migrating from a real .env file excludes ALL secret defaults.

        When users accidentally migrate from .env instead of .env.example,
        we should never copy real secret values into the schema.
        """
        runner = CliRunner()

        # Simulate a real .env file with actual secrets
        real_env = tmp_path / ".env"
        real_env.write_text(
            """# Real secrets (should NEVER go in schema)
DATABASE_PASSWORD=RealPassword123!
JWT_SECRET=actual-jwt-secret-key-xyz
STRIPE_API_KEY=sxsxk_live_actual_stripe_key

# Non-secrets
PORT=3000
DEBUG=false
"""
        )

        output_schema = tmp_path / ".tripwire.toml"

        # User confirms to proceed despite warning
        result = runner.invoke(
            main,
            [
                "schema",
                "from-example",
                "--source",
                str(real_env),
                "--output",
                str(output_schema),
            ],
            input="y\n",  # Confirm despite warning
        )

        # Should show warning about real env file
        assert "WARNING" in result.output
        assert "real environment file" in result.output

        # Load the generated schema
        with open(output_schema, "rb") as f:
            schema_data = tomllib.load(f)

        # CRITICAL: None of the secrets should have defaults
        password_var = schema_data["variables"]["DATABASE_PASSWORD"]
        jwt_var = schema_data["variables"]["JWT_SECRET"]
        stripe_var = schema_data["variables"]["STRIPE_API_KEY"]

        assert password_var.get("secret") is True
        assert jwt_var.get("secret") is True
        assert stripe_var.get("secret") is True

        # The security fix ensures these are NEVER included
        assert "default" not in password_var, "Real password should not be in schema!"
        assert "default" not in jwt_var, "Real JWT secret should not be in schema!"
        assert "default" not in stripe_var, "Real Stripe key should not be in schema!"

        # Non-secrets should still work
        port_var = schema_data["variables"]["PORT"]
        assert "default" in port_var
        assert port_var["default"] == 3000

    def test_schema_from_example_with_mixed_secrets(self, tmp_path: Path) -> None:
        """Test that only secrets are filtered, not all variables."""
        runner = CliRunner()

        env_example = tmp_path / ".env.example"
        # Use realistic secret values that will be detected by the comprehensive secret scanner
        env_example.write_text(
            """# Secrets (no defaults should be created)
API_KEY=sk-1234567890abcdef1234567890abcdef
DATABASE_PASSWORD=MySuperSecretPassword123!
JWT_SECRET=xeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
STRIPE_SECRET_KEY=xssk_live_1234567890abcdefghijklmnop

# Non-secrets (defaults should be preserved)
PORT=8080
TIMEOUT=30
MAX_CONNECTIONS=100
DEBUG=true
APP_NAME=MyApp
"""
        )

        output_schema = tmp_path / ".tripwire.toml"

        result = runner.invoke(
            main,
            [
                "schema",
                "from-example",
                "--source",
                str(env_example),
                "--output",
                str(output_schema),
            ],
        )

        assert result.exit_code == 0

        with open(output_schema, "rb") as f:
            schema_data = tomllib.load(f)

        variables = schema_data["variables"]

        # All secrets should have no defaults
        secret_vars = ["API_KEY", "DATABASE_PASSWORD", "JWT_SECRET", "AWS_SECRET_ACCESS_KEY", "STRIPE_SECRET_KEY"]
        for var_name in secret_vars:
            var_config = variables[var_name]
            assert var_config.get("secret") is True, f"{var_name} should be marked as secret"
            assert "default" not in var_config, f"{var_name} should not have default (security risk)"

        # All non-secrets should have defaults
        non_secret_vars = {
            "PORT": 8080,
            "TIMEOUT": 30,
            "MAX_CONNECTIONS": 100,
            "DEBUG": True,
            "APP_NAME": "MyApp",
        }
        for var_name, expected_default in non_secret_vars.items():
            var_config = variables[var_name]
            assert not var_config.get("secret", False), f"{var_name} should not be marked as secret"
            assert "default" in var_config, f"{var_name} should have default"
            assert var_config["default"] == expected_default, f"{var_name} default value mismatch"
