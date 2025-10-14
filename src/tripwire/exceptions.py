"""Custom exceptions for TripWire.

This module defines all custom exception types used throughout TripWire for
precise error handling and reporting.
"""

from pathlib import Path
from typing import Any, List, Optional, Union


class TripWireError(Exception):
    """Base exception for all TripWire errors."""

    pass


class MissingVariableError(TripWireError):
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
            f"\n[X] Missing required environment variable: {variable_name}",
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
                "[Tip] Run 'tripwire init' to create starter files",
                "",
            ]
        )

        message = "\n".join(lines)
        super().__init__(message)


class ValidationError(TripWireError):
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


class TypeCoercionError(TripWireError):
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


class EnvFileNotFoundError(TripWireError):
    """Raised when a required .env file is not found."""

    def __init__(self, file_path: str) -> None:
        """Initialize EnvFileNotFoundError.

        Args:
            file_path: Path to the missing .env file
        """
        self.file_path = file_path
        message = f"Environment file not found: {file_path}"
        super().__init__(message)


class SecretDetectedError(TripWireError):
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


class DriftError(TripWireError):
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


class GitAuditError(TripWireError):
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


class TripWireMultiValidationError(TripWireError):
    """Raised when multiple environment variables have validation errors.

    This exception provides a comprehensive error report showing all failures at once,
    dramatically improving developer experience by eliminating the fix-run-fix-run cycle.

    Attributes:
        errors: List of ValidationError instances collected during validation
        error_count: Number of validation errors found
    """

    def __init__(self, errors: List[ValidationError]) -> None:
        """Initialize TripWireMultiValidationError.

        Args:
            errors: List of ValidationError instances to report together
        """
        self.errors = errors
        self.error_count = len(errors)
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format multi-error message with clear, actionable guidance.

        Returns:
            Formatted error message with all validation failures and fix suggestions
        """
        lines = [
            "",
            f"TripWire found {self.error_count} environment variable error(s):",
            "",
        ]

        for idx, error in enumerate(self.errors, 1):
            lines.append(f"  {idx}. {error.variable_name}")
            lines.append(f"     ├─ Error: {error.reason}")

            if error.value:
                lines.append(f"     ├─ Received: {repr(error.value)}")
            else:
                lines.append(f"     ├─ Received: (not set)")

            # Add helpful fix suggestion
            fix_suggestion = self._get_fix_suggestion(error)
            if fix_suggestion:
                lines.append(f"     └─ Fix: {fix_suggestion}")

            lines.append("")  # Blank line between errors

        lines.append("Fix all variables and restart the application.")
        lines.append("Need help? Check your .env file or run: tripwire check")
        lines.append("")

        return "\n".join(lines)

    def _get_fix_suggestion(self, error: ValidationError) -> str:
        """Generate context-specific fix suggestion based on error reason.

        Args:
            error: ValidationError to generate suggestion for

        Returns:
            Actionable fix suggestion string
        """
        reason = error.reason.lower()

        # Missing variable
        if "required but not set" in reason or "missing" in reason:
            return f"Set {error.variable_name} in your .env file"

        # Format validation errors
        if "invalid format" in reason:
            if "postgresql" in reason:
                return "Use format: postgresql://user:pass@host:port/db"
            elif "mysql" in reason:
                return "Use format: mysql://user:pass@host:port/db"
            elif "email" in reason:
                return "Use format: user@example.com"
            elif "url" in reason:
                return "Add protocol scheme (https://...)"
            elif "uuid" in reason:
                return "Use format: 550e8400-e29b-41d4-a716-446655440000"
            elif "ipv4" in reason:
                return "Use format: 192.168.1.1"

        # Length validation errors
        if "min_length" in reason or "too short" in reason or "at least" in reason:
            return f"Provide a longer value for {error.variable_name}"
        elif "max_length" in reason or "too long" in reason or "at most" in reason:
            return f"Shorten {error.variable_name}"

        # Range validation errors
        if "min_val" in reason or "minimum" in reason or "out of range" in reason:
            if ">" in reason or ">=" in reason:
                return f"Increase {error.variable_name} value"
        if "max_val" in reason or "maximum" in reason or "out of range" in reason:
            if "<" in reason or "<=" in reason:
                return f"Decrease {error.variable_name} value"

        # Choices validation
        if "not in allowed choices" in reason or "allowed values" in reason:
            return f"Check allowed values for {error.variable_name}"

        # Pattern validation
        if "does not match pattern" in reason or "pattern" in reason:
            return f"Ensure {error.variable_name} matches the required pattern"

        # Type coercion errors
        if "cannot coerce" in reason or "type" in reason:
            return f"Check that {error.variable_name} has the correct data type"

        # Generic fallback
        return f"Check {error.variable_name} value in your .env file"
