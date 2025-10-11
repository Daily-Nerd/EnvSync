"""Test schema validation in CI/CD contexts.

Tests the graceful degradation behavior for missing .env files in CI/CD
environments where .env is correctly not committed to version control.
"""

import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from tripwire.cli.commands.schema import schema_validate


class TestCICDValidation:
    """Test schema validation behavior in CI/CD environments."""

    @pytest.fixture
    def temp_project(self, tmp_path, monkeypatch):
        """Create a temporary project with schema file and change to it."""
        # Create schema file
        schema_content = """
[project]
name = "test-project"
version = "1.0.0"

[variables.DATABASE_URL]
type = "string"
required = true
format = "postgresql"
description = "Database connection"

[variables.DEBUG]
type = "bool"
required = false
default = false
description = "Debug mode"
"""
        schema_path = tmp_path / ".tripwire.toml"
        schema_path.write_text(schema_content)

        # Change to the temp directory
        monkeypatch.chdir(tmp_path)

        return tmp_path

    @pytest.fixture
    def temp_env_file(self, temp_project):
        """Create a .env file in temp project."""
        env_path = temp_project / ".env"
        env_content = """DATABASE_URL=postgresql://localhost:5432/test
DEBUG=true
"""
        env_path.write_text(env_content)
        return env_path

    def test_strict_mode_missing_env_passes(self, temp_project):
        """Test that strict mode passes when .env doesn't exist (CI/CD scenario)."""
        runner = CliRunner()

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        assert result.exit_code == 0
        assert "not found (expected in CI/CD" in result.output
        assert "Validation passed" in result.output

    def test_strict_mode_with_fail_if_missing_fails(self, temp_project):
        """Test that --fail-if-missing overrides strict mode behavior."""
        runner = CliRunner()

        result = runner.invoke(
            schema_validate,
            [
                "--env-file",
                ".env",
                "--schema-file",
                ".tripwire.toml",
                "--strict",
                "--fail-if-missing",
            ],
        )

        assert result.exit_code == 1
        assert ".env does not exist" in result.output

    def test_local_mode_missing_env_fails_helpfully(self, temp_project):
        """Test that local mode (no strict) fails helpfully when .env missing."""
        runner = CliRunner()

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml"],
        )

        assert result.exit_code == 1
        assert ".env not found" in result.output
        assert "tripwire schema to-env" in result.output  # Helpful suggestion

    def test_strict_mode_with_existing_env_validates(self, temp_project, temp_env_file):
        """Test that strict mode validates .env if it exists."""
        runner = CliRunner()

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should validate successfully
        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_strict_mode_skips_gitignored_files(self, temp_project, temp_env_file):
        """Test that strict mode skips files in .gitignore (pre-commit context)."""
        runner = CliRunner()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )

        # Add .env to .gitignore
        gitignore = temp_project / ".gitignore"
        gitignore.write_text(".env\n")

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        assert result.exit_code == 0
        assert "Skipping .env (in .gitignore" in result.output
        assert "Validation skipped" in result.output

    def test_local_mode_validates_even_if_gitignored(self, temp_project, temp_env_file):
        """Test that local mode validates .env even if in .gitignore."""
        runner = CliRunner()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=temp_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )

        # Add .env to .gitignore
        gitignore = temp_project / ".gitignore"
        gitignore.write_text(".env\n")

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml"],  # No --strict
        )

        # Should still validate
        assert result.exit_code == 0
        assert "Validation passed" in result.output
        assert "Skipping" not in result.output

    def test_strict_mode_validates_non_gitignored_env(self, temp_project, temp_env_file):
        """Test that strict mode validates .env if NOT in .gitignore (warning case)."""
        runner = CliRunner()

        # Initialize git repo but DON'T add .env to .gitignore
        subprocess.run(["git", "init"], cwd=temp_project, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=temp_project,
            check=True,
            capture_output=True,
        )

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should validate (and fail because not in .gitignore is a problem)
        assert "Validating .env" in result.output
        # Should still pass validation if content is correct
        assert result.exit_code == 0

    def test_ci_environment_detection_simulation(self, temp_project, monkeypatch):
        """Test behavior when CI environment variables are present."""
        runner = CliRunner()

        # Simulate CI environment
        monkeypatch.setenv("CI", "true")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should pass in CI with missing .env
        assert result.exit_code == 0
        assert "Validation passed" in result.output

    def test_missing_schema_file_fails(self, temp_project):
        """Test that missing schema file fails regardless of mode."""
        runner = CliRunner()

        # Delete schema file
        schema_path = temp_project / ".tripwire.toml"
        if schema_path.exists():
            schema_path.unlink()

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Exit code 2 = Click option validation error (file doesn't exist)
        assert result.exit_code == 2
        assert "does not exist" in result.output

    def test_invalid_env_file_fails_in_strict_mode(self, temp_project):
        """Test that invalid .env content fails in strict mode."""
        runner = CliRunner()

        # Create invalid .env (missing required var)
        env_path = temp_project / ".env"
        env_content = """DEBUG=true
# Missing DATABASE_URL (required)
"""
        env_path.write_text(env_content)

        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should fail validation
        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_custom_environment_parameter(self, temp_project):
        """Test that custom environment parameter works with strict mode."""
        runner = CliRunner()

        result = runner.invoke(
            schema_validate,
            [
                "--env-file",
                ".env",
                "--schema-file",
                ".tripwire.toml",
                "--environment",
                "production",
                "--strict",
            ],
        )

        # Should pass (no .env, which is expected in CI)
        assert result.exit_code == 0
        assert "Validation passed" in result.output


class TestPreCommitHookIntegration:
    """Test pre-commit hook integration scenarios."""

    @pytest.fixture
    def git_project(self, tmp_path, monkeypatch):
        """Create a git project with TripWire setup."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create schema
        schema_content = """
[project]
name = "test-project"

[variables.API_KEY]
type = "string"
required = true
secret = true
"""
        schema_path = tmp_path / ".tripwire.toml"
        schema_path.write_text(schema_content)

        # Create .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".env\n*.log\n")

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        return tmp_path

    def test_hook_command_in_ci_without_env(self, git_project):
        """Simulate pre-commit hook command in CI/CD without .env."""
        runner = CliRunner()

        # Run the exact command used in pre-commit hooks
        result = runner.invoke(
            schema_validate,
            ["--strict"],  # Uses default .env and .tripwire.toml
        )

        # Should pass cleanly in CI
        assert result.exit_code == 0
        assert "Validation passed" in result.output or "expected in CI/CD" in result.output

    def test_hook_command_locally_with_gitignored_env(self, git_project):
        """Simulate pre-commit hook with local .env in .gitignore."""
        runner = CliRunner()

        # Create .env with local secrets
        env_path = git_project / ".env"
        env_content = """API_KEY=sk_test_1234567890abcdef
"""
        env_path.write_text(env_content)

        # Run hook command
        result = runner.invoke(
            schema_validate,
            ["--strict"],
        )

        # Should skip .env (it's in .gitignore)
        assert result.exit_code == 0
        assert "Skipping .env" in result.output

    def test_hook_command_with_uncommitted_env_not_in_gitignore(self, git_project):
        """Test warning scenario: .env exists but not in .gitignore."""
        runner = CliRunner()

        # Remove .env from .gitignore
        gitignore = git_project / ".gitignore"
        gitignore.write_text("*.log\n")  # Remove .env

        # Create .env
        env_path = git_project / ".env"
        env_content = """API_KEY=sk_test_1234567890abcdef
"""
        env_path.write_text(env_content)

        # Run hook command
        result = runner.invoke(
            schema_validate,
            ["--strict"],
        )

        # Should validate (and potentially warn about .env not being ignored)
        assert "Validating .env" in result.output


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_nonexistent_custom_env_file_strict_mode(self, tmp_path, monkeypatch):
        """Test strict mode with custom (non-existent) env file."""
        schema_path = tmp_path / ".tripwire.toml"
        schema_path.write_text('[project]\nname = "test"')

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env.production", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should pass (missing file in CI/CD is expected)
        assert result.exit_code == 0
        assert ".env.production not found" in result.output

    def test_both_strict_and_fail_if_missing(self, tmp_path, monkeypatch):
        """Test that --fail-if-missing overrides --strict."""
        schema_path = tmp_path / ".tripwire.toml"
        schema_path.write_text('[project]\nname = "test"')

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            schema_validate,
            [
                "--env-file",
                ".env",
                "--schema-file",
                ".tripwire.toml",
                "--strict",
                "--fail-if-missing",
            ],
        )

        # Should fail (--fail-if-missing takes precedence)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_empty_env_file(self, tmp_path, monkeypatch):
        """Test validation of empty .env file."""
        schema_content = """
[project]
name = "test"

[variables.REQUIRED_VAR]
type = "string"
required = true
"""
        schema_path = tmp_path / ".tripwire.toml"
        schema_path.write_text(schema_content)

        env_path = tmp_path / ".env"
        env_path.write_text("")  # Empty file

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            schema_validate,
            ["--env-file", ".env", "--schema-file", ".tripwire.toml", "--strict"],
        )

        # Should fail (missing required variable)
        assert result.exit_code == 1
        assert "Validation failed" in result.output
