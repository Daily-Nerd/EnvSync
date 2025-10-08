"""Integration tests for audit --all auto-detection feature.

This module tests the auto-detection functionality of the audit command
when using the --all flag to scan all secrets in the .env file.
"""

import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_git_repo_with_env(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository with .env file containing secrets.

    Yields:
        Path to temporary repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    # Disable GPG signing for tests
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create .env file with secrets
    env_content = """# Test environment file
DATABASE_URL=postgresql://user:password@localhost:5432/db
API_KEY=sk-test-1234567890abcdef1234567890abcdef
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
DEBUG=true
"""
    env_file = repo_path / ".env"
    env_file.write_text(env_content)

    # Commit the .env file
    subprocess.run(["git", "add", ".env"], cwd=repo_path, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "commit", "-m", "Add environment variables"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    # Git commit might fail if no changes, that's okay
    if result.returncode != 0 and "nothing to commit" not in result.stdout.lower():
        raise RuntimeError(f"Git commit failed: {result.stderr}")

    yield repo_path


class TestAuditAutoDetection:
    """Tests for audit --all auto-detection feature."""

    def test_audit_all_flag_detects_secrets(self, temp_git_repo_with_env: Path) -> None:
        """Test that --all flag detects all secrets in .env file.

        This verifies that the auto-detection mode scans the .env file,
        identifies secrets, and audits their git history.
        """
        # Run tripwire audit --all
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "--all"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should succeed (exit code 0)
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Output should contain auto-detection message
        assert "Auto-detecting secrets" in result.stdout
        assert "Found" in result.stdout and "potential secret" in result.stdout

        # Should detect AWS keys
        assert "AWS_ACCESS_KEY_ID" in result.stdout or "AWS" in result.stdout
        assert "AWS_SECRET_ACCESS_KEY" in result.stdout or "AWS" in result.stdout

    def test_audit_all_json_output(self, temp_git_repo_with_env: Path) -> None:
        """Test that --all flag works with --json output."""
        import json

        # Run tripwire audit --all --json
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "--all", "--json"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should succeed
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\n{result.stdout}")

        # Verify structure
        assert "total_secrets_found" in output
        assert "secrets" in output
        assert isinstance(output["secrets"], list)
        assert output["total_secrets_found"] > 0

        # Check that secrets are properly formatted
        for secret in output["secrets"]:
            assert "variable_name" in secret
            assert "secret_type" in secret
            assert "severity" in secret
            assert "status" in secret

    def test_audit_all_with_no_env_file(self, tmp_path: Path) -> None:
        """Test that --all flag shows error when .env file doesn't exist."""
        # Initialize git repo without .env file
        repo_path = tmp_path / "empty_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        # Run tripwire audit --all
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should fail with error
        assert result.returncode != 0
        assert ".env file not found" in result.stdout or "not found" in result.stdout.lower()

    def test_audit_all_with_no_secrets(self, tmp_path: Path) -> None:
        """Test that --all flag handles .env file with no secrets gracefully."""
        # Initialize git repo with clean .env file
        repo_path = tmp_path / "clean_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        # Create .env file with no secrets
        env_content = """# Clean environment file
DEBUG=true
PORT=8000
LOG_LEVEL=INFO
"""
        env_file = repo_path / ".env"
        env_file.write_text(env_content)

        # Run tripwire audit --all
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "--all"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should succeed with no secrets message
        assert result.returncode == 0
        assert "No secrets detected" in result.stdout or "appear secure" in result.stdout

    def test_audit_requires_secret_name_or_all_flag(self, temp_git_repo_with_env: Path) -> None:
        """Test that audit command requires either SECRET_NAME or --all flag."""
        # Run tripwire audit without arguments
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should fail with error
        assert result.returncode != 0
        assert "Must provide SECRET_NAME or use --all flag" in result.stdout

    def test_audit_cannot_use_both_name_and_all(self, temp_git_repo_with_env: Path) -> None:
        """Test that audit command cannot use both SECRET_NAME and --all flag."""
        # Run tripwire audit AWS_ACCESS_KEY_ID --all
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "AWS_ACCESS_KEY_ID", "--all"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should fail with error
        assert result.returncode != 0
        assert "Cannot use both" in result.stdout or "SECRET_NAME and --all" in result.stdout


class TestAuditVisualTimeline:
    """Tests for visual timeline and blast radius features."""

    def test_combined_timeline_display(self, temp_git_repo_with_env: Path) -> None:
        """Test that combined visual timeline is displayed for multiple secrets."""
        # Run tripwire audit --all
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "--all"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should succeed
        assert result.returncode == 0

        # Should show blast radius visualization
        assert "Secret Leak Blast Radius" in result.stdout or "Blast Radius" in result.stdout
        assert "Summary" in result.stdout or "Total commits" in result.stdout

    def test_single_secret_timeline_display(self, temp_git_repo_with_env: Path) -> None:
        """Test that single secret timeline is displayed properly."""
        # Run tripwire audit for a specific secret
        result = subprocess.run(
            [sys.executable, "-m", "tripwire.cli", "audit", "AWS_ACCESS_KEY_ID"],
            cwd=temp_git_repo_with_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # Should succeed
        assert result.returncode == 0

        # Should show timeline for the secret
        assert "AWS_ACCESS_KEY_ID" in result.stdout
        assert "Timeline" in result.stdout or "Security Impact" in result.stdout
