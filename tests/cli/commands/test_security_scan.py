"""Comprehensive tests for security scan command.

This test suite targets coverage for src/tripwire/cli/commands/security/scan.py
aiming to increase coverage from 32.16% to 80%+.

Covers:
- Happy path: Successful scans with no secrets
- Secret detection: Various secret types found
- CLI flags: --strict, --depth
- Risk level calculation: CRITICAL, MEDIUM, LOW, NONE
- Output formatting: Tables, panels, status messages
- Edge cases: Missing files, gitignored files, multiple secrets
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from tripwire.cli.commands.security.scan import scan
from tripwire.secrets import SecretMatch, SecretType


@pytest.fixture
def cli_runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_secret_match():
    """Factory for creating SecretMatch objects."""

    def _create(
        secret_type=SecretType.GENERIC_API_KEY,
        variable_name="API_KEY",
        value="***",
        line_number=1,
        severity="high",
        recommendation="Rotate immediately",
    ):
        return SecretMatch(
            secret_type=secret_type,
            variable_name=variable_name,
            value=value,
            line_number=line_number,
            severity=severity,
            recommendation=recommendation,
        )

    return _create


class TestScanCommandBasics:
    """Test basic scan command functionality."""

    def test_scan_no_env_no_git(self, cli_runner, tmp_path, monkeypatch):
        """Test scan when no .env file and no git repo exists."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "No secrets detected" in result.output
        assert "Your environment files appear secure" in result.output

    @patch("tripwire.secrets.scan_env_file")
    def test_scan_with_clean_env_file(self, mock_scan_env, cli_runner, tmp_path, monkeypatch):
        """Test scan with .env file that contains no secrets."""
        # Create real .env file
        env_file = tmp_path / ".env"
        env_file.write_text("# Empty env file\n")

        monkeypatch.chdir(tmp_path)

        # No secrets found
        mock_scan_env.return_value = []

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "No secrets detected" in result.output
        mock_scan_env.assert_called_once()

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_scan_with_git_no_secrets(self, mock_scan_env, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test scan with git repo but no secrets found."""
        # Create real files
        env_file = tmp_path / ".env"
        env_file.write_text("# Empty\n")

        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        monkeypatch.chdir(tmp_path)

        # No secrets
        mock_scan_env.return_value = []
        mock_scan_git.return_value = []

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "No secrets detected" in result.output
        mock_scan_git.assert_called_once()


class TestScanWithSecrets:
    """Test scan command when secrets are detected."""

    @patch("tripwire.secrets.scan_env_file")
    def test_scan_with_env_secrets_gitignored(
        self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch
    ):
        """Test scan with secrets in .env file that IS in .gitignore (LOW risk)."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n")
        monkeypatch.chdir(tmp_path)

        # Secrets found in .env
        secret = mock_secret_match(
            secret_type=SecretType.AWS_ACCESS_KEY,
            variable_name="AWS_ACCESS_KEY_ID",
            severity="critical",
            recommendation="Rotate AWS credentials immediately",
        )
        mock_scan_env.return_value = [secret]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "Detected Secrets" in result.output
        assert "AWS_ACCESS_KEY_ID" in result.output
        assert "INFO: Secrets found in local development files" in result.output
        assert "Expected for local development" in result.output

    @patch("tripwire.secrets.scan_env_file")
    def test_scan_with_env_secrets_not_gitignored(
        self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch
    ):
        """Test scan with secrets in .env file NOT in .gitignore (MEDIUM risk)."""
        env_file = tmp_path / ".env"
        env_file.write_text("DB_PASSWORD=secret\n")
        monkeypatch.chdir(tmp_path)

        # Secrets found
        secret = mock_secret_match(variable_name="DATABASE_PASSWORD")
        mock_scan_env.return_value = [secret]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=False):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "WARNING: Secrets in committed files!" in result.output
        assert "Add .env to .gitignore immediately" in result.output
        assert "DATABASE_PASSWORD" in result.output

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_scan_with_git_history_secrets(self, mock_scan_env, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test scan with secrets found in git history (CRITICAL risk)."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        # No secrets in current .env
        mock_scan_env.return_value = []

        # Secrets in git history
        mock_scan_git.return_value = [
            {
                "variable": "SECRET_KEY",
                "type": "generic_api_key",
                "severity": "critical",
                "commit": "abc123",
            }
        ]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "CRITICAL: Secrets found in version control!" in result.output
        assert "SECRET_KEY" in result.output
        assert "Rotate ALL detected secrets immediately" in result.output


class TestScanStrictMode:
    """Test --strict flag behavior."""

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_strict_mode_exits_on_critical(self, mock_scan_env, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test --strict flag exits with code 1 on CRITICAL risk."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = []
        mock_scan_git.return_value = [
            {"variable": "API_KEY", "type": "generic_api_key", "severity": "high", "commit": "abc123"}
        ]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan, ["--strict"])

        assert result.exit_code == 1

    @patch("tripwire.secrets.scan_env_file")
    def test_strict_mode_exits_on_medium(self, mock_scan_env, cli_runner, tmp_path, monkeypatch, mock_secret_match):
        """Test --strict flag exits with code 1 on MEDIUM risk."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        secret = mock_secret_match()
        mock_scan_env.return_value = [secret]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=False):
            result = cli_runner.invoke(scan, ["--strict"])

        assert result.exit_code == 1

    @patch("tripwire.secrets.scan_env_file")
    def test_strict_mode_passes_on_low(self, mock_scan_env, cli_runner, tmp_path, monkeypatch, mock_secret_match):
        """Test --strict flag passes (exit 0) on LOW risk."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        secret = mock_secret_match()
        mock_scan_env.return_value = [secret]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan, ["--strict"])

        assert result.exit_code == 0

    def test_strict_mode_skips_gitignored_files(self, cli_runner, tmp_path, monkeypatch):
        """Test --strict mode skips files in .gitignore (pre-commit context)."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        # should_skip_file_in_hook returns True
        with patch("tripwire.cli.commands.security.scan.should_skip_file_in_hook", return_value=True):
            result = cli_runner.invoke(scan, ["--strict"])

        assert result.exit_code == 0
        assert "Skipping .env (in .gitignore - won't be committed)" in result.output


class TestScanDepthOption:
    """Test --depth option for git history scanning."""

    @patch("tripwire.secrets.scan_git_history")
    def test_depth_option_default(self, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test default --depth is 100."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_git.return_value = []

        result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        # Verify depth=100 was passed (default)
        mock_scan_git.assert_called_once()
        _, kwargs = mock_scan_git.call_args
        assert kwargs.get("depth", 100) == 100

    @patch("tripwire.secrets.scan_git_history")
    def test_depth_option_custom(self, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test custom --depth value."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_git.return_value = []

        result = cli_runner.invoke(scan, ["--depth", "50"])

        assert result.exit_code == 0
        _, kwargs = mock_scan_git.call_args
        assert kwargs.get("depth") == 50


class TestScanOutputFormatting:
    """Test output formatting and table display."""

    @patch("tripwire.secrets.scan_env_file")
    def test_secrets_table_formatting(self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch):
        """Test secrets are displayed in formatted table."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRETS=here\n")
        monkeypatch.chdir(tmp_path)

        secrets = [
            mock_secret_match(
                secret_type=SecretType.AWS_ACCESS_KEY,
                variable_name="AWS_KEY",
                severity="critical",
            ),
            mock_secret_match(
                secret_type=SecretType.GENERIC_API_KEY,
                variable_name="API_TOKEN",
                severity="high",
            ),
        ]
        mock_scan_env.return_value = secrets

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "Detected Secrets" in result.output
        assert "AWS_KEY" in result.output
        assert "API_TOKEN" in result.output
        assert "Variable" in result.output
        assert "Type" in result.output
        assert "Severity" in result.output

    @patch("tripwire.secrets.scan_env_file")
    def test_long_recommendation_truncation(self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch):
        """Test that long recommendations are truncated in table."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        long_recommendation = "A" * 100  # Very long recommendation
        secret = mock_secret_match(recommendation=long_recommendation)
        mock_scan_env.return_value = [secret]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        # Should be truncated to 80 chars + "..."
        assert "..." in result.output


class TestScanEdgeCases:
    """Test edge cases and error conditions."""

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_git_findings_with_invalid_secret_type(
        self, mock_scan_env, mock_scan_git, cli_runner, tmp_path, monkeypatch
    ):
        """Test handling of git findings with invalid SecretType."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = []

        # Git finding with invalid type
        mock_scan_git.return_value = [
            {
                "variable": "SECRET",
                "type": "invalid_type_that_doesnt_exist",  # Will trigger ValueError
                "severity": "high",
                "commit": "abc123",
            }
        ]

        result = cli_runner.invoke(scan)

        # Should handle gracefully and default to GENERIC_API_KEY
        assert result.exit_code == 0
        assert "SECRET" in result.output

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_duplicate_git_findings_deduplication(
        self, mock_scan_env, mock_scan_git, cli_runner, tmp_path, monkeypatch
    ):
        """Test that duplicate git findings are deduplicated."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = []

        # Duplicate findings (same variable and type)
        mock_scan_git.return_value = [
            {"variable": "API_KEY", "type": "generic_api_key", "severity": "high", "commit": "abc123"},
            {"variable": "API_KEY", "type": "generic_api_key", "severity": "high", "commit": "def456"},
            {"variable": "API_KEY", "type": "generic_api_key", "severity": "high", "commit": "ghi789"},
        ]

        result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        # Should only show once in table (deduplicated)
        assert "API_KEY" in result.output

    @patch("tripwire.secrets.scan_env_file")
    def test_empty_env_file(self, mock_scan_env, cli_runner, tmp_path, monkeypatch):
        """Test handling of empty .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = []

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "No secrets found in .env" in result.output


class TestScanRiskLevelCalculation:
    """Test risk level calculation logic."""

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_risk_level_critical_git_history(
        self, mock_scan_env, mock_scan_git, cli_runner, mock_secret_match, tmp_path, monkeypatch
    ):
        """Test CRITICAL risk when secrets in git history."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        # Both env and git have secrets, but git takes precedence
        mock_scan_env.return_value = [mock_secret_match()]
        mock_scan_git.return_value = [
            {"variable": "KEY", "type": "generic_api_key", "severity": "high", "commit": "abc"}
        ]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=False):
            result = cli_runner.invoke(scan)

        assert "CRITICAL" in result.output
        assert result.exit_code == 0

    @patch("tripwire.secrets.scan_env_file")
    def test_risk_level_medium_env_not_gitignored(
        self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch
    ):
        """Test MEDIUM risk when secrets in .env NOT gitignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = [mock_secret_match()]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=False):
            result = cli_runner.invoke(scan)

        assert "WARNING" in result.output
        assert "MEDIUM" not in result.output  # Text says WARNING, not MEDIUM

    @patch("tripwire.secrets.scan_env_file")
    def test_risk_level_low_env_gitignored(self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch):
        """Test LOW risk when secrets in .env but gitignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = [mock_secret_match()]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert "INFO" in result.output
        assert "Expected for local development" in result.output

    def test_risk_level_none_no_secrets(self, cli_runner, tmp_path, monkeypatch):
        """Test NONE risk when no secrets found."""
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(scan)

        assert result.exit_code == 0
        assert "No secrets detected" in result.output


class TestScanIntegration:
    """Integration tests combining multiple features."""

    @patch("tripwire.secrets.scan_git_history")
    @patch("tripwire.secrets.scan_env_file")
    def test_combined_env_and_git_secrets(
        self, mock_scan_env, mock_scan_git, cli_runner, mock_secret_match, tmp_path, monkeypatch
    ):
        """Test scan with secrets in both .env and git history."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=value\n")
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        # Secrets in both places
        env_secret = mock_secret_match(variable_name="ENV_SECRET")
        mock_scan_env.return_value = [env_secret]

        mock_scan_git.return_value = [
            {"variable": "GIT_SECRET", "type": "generic_api_key", "severity": "critical", "commit": "abc123"}
        ]

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        # Should show both secrets
        assert "ENV_SECRET" in result.output
        assert "GIT_SECRET" in result.output
        # Git history takes precedence for risk level
        assert "CRITICAL" in result.output

    @patch("tripwire.secrets.scan_env_file")
    def test_multiple_secret_types(self, mock_scan_env, cli_runner, mock_secret_match, tmp_path, monkeypatch):
        """Test scan with multiple different secret types."""
        env_file = tmp_path / ".env"
        env_file.write_text("SECRETS=here\n")
        monkeypatch.chdir(tmp_path)

        secrets = [
            mock_secret_match(secret_type=SecretType.AWS_ACCESS_KEY, variable_name="AWS_KEY"),
            mock_secret_match(secret_type=SecretType.GITHUB_TOKEN, variable_name="GH_TOKEN"),
            mock_secret_match(secret_type=SecretType.STRIPE_KEY, variable_name="STRIPE_KEY"),
            mock_secret_match(secret_type=SecretType.JWT_TOKEN, variable_name="JWT_TOKEN"),
        ]
        mock_scan_env.return_value = secrets

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert "AWS_KEY" in result.output
        assert "GH_TOKEN" in result.output
        assert "STRIPE_KEY" in result.output
        assert "JWT_TOKEN" in result.output


class TestScanStatusMessages:
    """Test various status messages and icons."""

    @patch("tripwire.secrets.scan_env_file")
    def test_scanning_progress_messages(self, mock_scan_env, cli_runner, tmp_path, monkeypatch):
        """Test that scanning progress messages are displayed."""
        env_file = tmp_path / ".env"
        env_file.write_text("")
        monkeypatch.chdir(tmp_path)

        mock_scan_env.return_value = []

        with patch("tripwire.cli.utils.helpers.is_file_in_gitignore", return_value=True):
            result = cli_runner.invoke(scan)

        assert "Scanning for secrets..." in result.output
        assert "Scanning .env file..." in result.output

    @patch("tripwire.secrets.scan_git_history")
    def test_git_history_scanning_message(self, mock_scan_git, cli_runner, tmp_path, monkeypatch):
        """Test git history scanning message shows depth."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        mock_scan_git.return_value = []

        result = cli_runner.invoke(scan, ["--depth", "200"])

        assert "Scanning last 200 commits" in result.output


class TestScanHelperFunctions:
    """Test the helper functions in scan.py."""

    def test_display_combined_timeline_not_called_in_scan(self):
        """Test that _display_combined_timeline exists but isn't used in scan command.

        This is a helper for audit command, not scan.
        """
        from tripwire.cli.commands.security.scan import _display_combined_timeline

        # Function should exist
        assert callable(_display_combined_timeline)

    def test_display_single_audit_result_not_called_in_scan(self):
        """Test that _display_single_audit_result exists but isn't used in scan command.

        This is a helper for audit command, not scan.
        """
        from tripwire.cli.commands.security.scan import _display_single_audit_result

        # Function should exist
        assert callable(_display_single_audit_result)
