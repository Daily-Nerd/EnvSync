"""Custom exceptions for EnvSync.

This module defines all custom exception types used throughout EnvSync for
precise error handling and reporting.
"""

from pathlib import Path
from typing import Any, List, Optional, Union


class EnvSyncError(Exception):
    """Base exception for all EnvSync errors."""

    pass


class MissingVariableError(EnvSyncError):
    """Raised when a required environment variable is missing."""

    def __init__(self, variable_name: str, description: Optional[str] = None) -> None:
        """Initialize MissingVariableError.

        Args:
            variable_name: Name of the missing environment variable
            description: Optional description of the variable's purpose
        """
        self.variable_name = variable_name
        self.description = description

        # Build multi-line helpful message
        lines = [
            f"\n❌ Missing required environment variable: {variable_name}",
            "",
        ]

        if description:
            lines.append(f"Description: {description}")
            lines.append("")

        lines.extend(
            [
                "To fix this, choose one option:",
                "",
                "  1. Add to .env file:",
                f"     {variable_name}=your-value-here",
                "",
                "  2. Set in your shell:",
                f"     export {variable_name}=your-value-here",
                "",
                "  3. Copy from example (if available):",
                "     cp .env.example .env",
                "",
                "💡 Tip: Run 'envsync init' to create starter files",
                "",
            ]
        )

        message = "\n".join(lines)
        super().__init__(message)


class ValidationError(EnvSyncError):
    """Raised when an environment variable fails validation."""

    def __init__(
        self,
        variable_name: str,
        value: Any,
        reason: str,
        expected: Optional[str] = None,
    ) -> None:
        """Initialize ValidationError.

        Args:
            variable_name: Name of the environment variable
            value: The value that failed validation
            reason: Reason for validation failure
            expected: Optional description of expected value format
        """
        self.variable_name = variable_name
        self.value = value
        self.reason = reason
        self.expected = expected

        message = f"Validation failed for {variable_name}: {reason}"
        if expected:
            message += f"\nExpected: {expected}"
        message += f"\nReceived: {value}"
        super().__init__(message)


class TypeCoercionError(EnvSyncError):
    """Raised when type coercion fails."""

    def __init__(
        self,
        variable_name: str,
        value: Any,
        target_type: type,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize TypeCoercionError.

        Args:
            variable_name: Name of the environment variable
            value: The value that couldn't be coerced
            target_type: The type we tried to coerce to
            original_error: Original exception that caused the failure
        """
        self.variable_name = variable_name
        self.value = value
        self.target_type = target_type
        self.original_error = original_error

        message = f"Cannot coerce {variable_name} to {target_type.__name__}: {value}"
        if original_error:
            message += f"\nReason: {original_error}"
        super().__init__(message)


class EnvFileNotFoundError(EnvSyncError):
    """Raised when a required .env file is not found."""

    def __init__(self, file_path: str) -> None:
        """Initialize EnvFileNotFoundError.

        Args:
            file_path: Path to the missing .env file
        """
        self.file_path = file_path
        message = f"Environment file not found: {file_path}"
        super().__init__(message)


class SecretDetectedError(EnvSyncError):
    """Raised when a secret is detected in an unsafe location."""

    def __init__(
        self,
        secret_type: str,
        location: str,
        variable_name: Optional[str] = None,
    ) -> None:
        """Initialize SecretDetectedError.

        Args:
            secret_type: Type of secret detected (e.g., "API key", "AWS access key")
            location: Where the secret was found (file path or git commit)
            variable_name: Optional name of the variable containing the secret
        """
        self.secret_type = secret_type
        self.location = location
        self.variable_name = variable_name

        message = f"Detected {secret_type} in {location}"
        if variable_name:
            message += f" (variable: {variable_name})"
        super().__init__(message)


class DriftError(EnvSyncError):
    """Raised when environment configuration has drifted from expected state."""

    def __init__(
        self,
        missing_vars: List[str],
        extra_vars: List[str],
    ) -> None:
        """Initialize DriftError.

        Args:
            missing_vars: List of variables missing from current environment
            extra_vars: List of variables present but not expected
        """
        self.missing_vars = missing_vars
        self.extra_vars = extra_vars

        parts = []
        if missing_vars:
            parts.append(f"Missing variables: {', '.join(missing_vars)}")
        if extra_vars:
            parts.append(f"Extra variables: {', '.join(extra_vars)}")
        message = "Environment drift detected\n" + "\n".join(parts)
        super().__init__(message)


class GitAuditError(EnvSyncError):
    """Base exception for git audit operations."""

    pass


class NotGitRepositoryError(GitAuditError):
    """Raised when current directory is not a git repository."""

    def __init__(self, path: Union[Path, str]) -> None:
        """Initialize NotGitRepositoryError.

        Args:
            path: Path that is not a git repository
        """
        self.path = path
        super().__init__(f"Not a git repository: {path}")


class GitCommandError(GitAuditError):
    """Raised when git command fails."""

    def __init__(self, command: str, stderr: str, returncode: int) -> None:
        """Initialize GitCommandError.

        Args:
            command: Git command that failed
            stderr: Standard error output
            returncode: Git command return code
        """
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"Git command failed (exit {returncode}): {command}\n{stderr}")
