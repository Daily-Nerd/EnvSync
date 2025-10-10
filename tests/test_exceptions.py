"""Tests for TripWire exception classes."""

import pytest

from tripwire.exceptions import (
    DriftError,
    EnvFileNotFoundError,
    GitAuditError,
    GitCommandError,
    MissingVariableError,
    NotGitRepositoryError,
    SecretDetectedError,
    TripWireError,
    TypeCoercionError,
    ValidationError,
)


class TestBaseExceptions:
    """Tests for base exception classes."""

    def test_tripwire_error(self) -> None:
        """Test TripWireError base exception."""
        error = TripWireError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_git_audit_error(self) -> None:
        """Test GitAuditError base exception."""
        error = GitAuditError("Test git error")
        assert str(error) == "Test git error"
        assert isinstance(error, TripWireError)


class TestMissingVariableError:
    """Tests for MissingVariableError."""

    def test_missing_variable_error_without_description(self) -> None:
        """Test MissingVariableError without description."""
        error = MissingVariableError("DATABASE_URL")
        error_str = str(error)

        assert "DATABASE_URL" in error_str
        assert "Missing required environment variable" in error_str
        assert "tripwire init" in error_str
        assert error.variable_name == "DATABASE_URL"
        assert error.description is None

    def test_missing_variable_error_with_description(self) -> None:
        """Test MissingVariableError with description."""
        error = MissingVariableError("DATABASE_URL", "Database connection string")
        error_str = str(error)

        assert "DATABASE_URL" in error_str
        assert "Database connection string" in error_str
        assert error.variable_name == "DATABASE_URL"
        assert error.description == "Database connection string"


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error_without_expected(self) -> None:
        """Test ValidationError without expected parameter."""
        error = ValidationError(
            variable_name="PORT",
            value="invalid",
            reason="Must be a number",
        )
        error_str = str(error)

        assert "PORT" in error_str
        assert "Must be a number" in error_str
        assert "invalid" in error_str
        assert error.variable_name == "PORT"
        assert error.value == "invalid"
        assert error.reason == "Must be a number"
        assert error.expected is None

    def test_validation_error_with_expected(self) -> None:
        """Test ValidationError with expected parameter."""
        error = ValidationError(
            variable_name="PORT",
            value="invalid",
            reason="Must be a number",
            expected="Integer between 1 and 65535",
        )
        error_str = str(error)

        assert "PORT" in error_str
        assert "Must be a number" in error_str
        assert "Integer between 1 and 65535" in error_str
        assert "invalid" in error_str
        assert error.expected == "Integer between 1 and 65535"


class TestTypeCoercionError:
    """Tests for TypeCoercionError."""

    def test_type_coercion_error_without_original(self) -> None:
        """Test TypeCoercionError without original_error."""
        error = TypeCoercionError(
            variable_name="PORT",
            value="not_a_number",
            target_type=int,
        )
        error_str = str(error)

        assert "PORT" in error_str
        assert "int" in error_str
        assert "not_a_number" in error_str
        assert error.variable_name == "PORT"
        assert error.value == "not_a_number"
        assert error.target_type == int
        assert error.original_error is None

    def test_type_coercion_error_with_original(self) -> None:
        """Test TypeCoercionError with original_error."""
        original = ValueError("Invalid literal for int()")
        error = TypeCoercionError(
            variable_name="PORT",
            value="not_a_number",
            target_type=int,
            original_error=original,
        )
        error_str = str(error)

        assert "PORT" in error_str
        assert "int" in error_str
        assert "Invalid literal" in error_str
        assert error.original_error == original


class TestEnvFileNotFoundError:
    """Tests for EnvFileNotFoundError."""

    def test_env_file_not_found_error(self) -> None:
        """Test EnvFileNotFoundError."""
        error = EnvFileNotFoundError(".env.production")
        error_str = str(error)

        assert ".env.production" in error_str
        assert "not found" in error_str
        assert error.file_path == ".env.production"


class TestSecretDetectedError:
    """Tests for SecretDetectedError."""

    def test_secret_detected_error_without_variable(self) -> None:
        """Test SecretDetectedError without variable_name."""
        error = SecretDetectedError(
            secret_type="AWS access key",
            location=".env",
        )
        error_str = str(error)

        assert "AWS access key" in error_str
        assert ".env" in error_str
        assert error.secret_type == "AWS access key"
        assert error.location == ".env"
        assert error.variable_name is None

    def test_secret_detected_error_with_variable(self) -> None:
        """Test SecretDetectedError with variable_name."""
        error = SecretDetectedError(
            secret_type="AWS access key",
            location=".env",
            variable_name="AWS_SECRET_KEY",
        )
        error_str = str(error)

        assert "AWS access key" in error_str
        assert ".env" in error_str
        assert "AWS_SECRET_KEY" in error_str
        assert error.variable_name == "AWS_SECRET_KEY"


class TestDriftError:
    """Tests for DriftError."""

    def test_drift_error_missing_only(self) -> None:
        """Test DriftError with only missing variables."""
        error = DriftError(
            missing_vars=["DATABASE_URL", "API_KEY"],
            extra_vars=[],
        )
        error_str = str(error)

        assert "DATABASE_URL" in error_str
        assert "API_KEY" in error_str
        assert "Missing variables" in error_str
        assert error.missing_vars == ["DATABASE_URL", "API_KEY"]
        assert error.extra_vars == []

    def test_drift_error_extra_only(self) -> None:
        """Test DriftError with only extra variables."""
        error = DriftError(
            missing_vars=[],
            extra_vars=["DEBUG", "TEST_MODE"],
        )
        error_str = str(error)

        assert "DEBUG" in error_str
        assert "TEST_MODE" in error_str
        assert "Extra variables" in error_str
        assert error.missing_vars == []
        assert error.extra_vars == ["DEBUG", "TEST_MODE"]

    def test_drift_error_both(self) -> None:
        """Test DriftError with both missing and extra variables."""
        error = DriftError(
            missing_vars=["DATABASE_URL"],
            extra_vars=["DEBUG"],
        )
        error_str = str(error)

        assert "DATABASE_URL" in error_str
        assert "DEBUG" in error_str
        assert "Missing variables" in error_str
        assert "Extra variables" in error_str


class TestGitErrors:
    """Tests for git-related errors."""

    def test_not_git_repository_error(self) -> None:
        """Test NotGitRepositoryError."""
        from pathlib import Path

        path = Path("/tmp/not_a_repo")
        error = NotGitRepositoryError(path)
        error_str = str(error)

        assert "not_a_repo" in error_str
        assert "Not a git repository" in error_str
        assert error.path == path

    def test_not_git_repository_error_string_path(self) -> None:
        """Test NotGitRepositoryError with string path."""
        error = NotGitRepositoryError("/tmp/not_a_repo")
        error_str = str(error)

        assert "not_a_repo" in error_str
        assert error.path == "/tmp/not_a_repo"

    def test_git_command_error(self) -> None:
        """Test GitCommandError."""
        error = GitCommandError(
            command="git status",
            stderr="fatal: not a git repository",
            returncode=128,
        )
        error_str = str(error)

        assert "git status" in error_str
        assert "fatal: not a git repository" in error_str
        assert "128" in error_str
        assert error.command == "git status"
        assert error.stderr == "fatal: not a git repository"
        assert error.returncode == 128


class TestExceptionInheritance:
    """Tests for exception inheritance and hierarchy."""

    def test_all_exceptions_inherit_from_tripwire_error(self) -> None:
        """Test that all custom exceptions inherit from TripWireError."""
        assert issubclass(MissingVariableError, TripWireError)
        assert issubclass(ValidationError, TripWireError)
        assert issubclass(TypeCoercionError, TripWireError)
        assert issubclass(EnvFileNotFoundError, TripWireError)
        assert issubclass(SecretDetectedError, TripWireError)
        assert issubclass(DriftError, TripWireError)
        assert issubclass(GitAuditError, TripWireError)

    def test_git_errors_inherit_from_git_audit_error(self) -> None:
        """Test that git errors inherit from GitAuditError."""
        assert issubclass(NotGitRepositoryError, GitAuditError)
        assert issubclass(GitCommandError, GitAuditError)

    def test_exception_can_be_caught_as_tripwire_error(self) -> None:
        """Test that all exceptions can be caught as TripWireError."""
        with pytest.raises(TripWireError):
            raise MissingVariableError("TEST")

        with pytest.raises(TripWireError):
            raise ValidationError("TEST", "value", "reason")

        with pytest.raises(TripWireError):
            raise GitCommandError("git", "error", 1)
