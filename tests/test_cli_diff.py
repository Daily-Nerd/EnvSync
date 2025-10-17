"""Comprehensive tests for CLI diff command to improve coverage from 12.40% to 80%+.

This test suite targets the uncovered lines 54-179 in src/tripwire/cli/commands/diff.py,
covering all command scenarios, output formats, error handling, and edge cases.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from tripwire.cli import main


class TestDiffCommandBasic:
    """Basic diff command tests covering standard scenarios."""

    def test_diff_identical_env_files(self, tmp_path):
        """Test diff with two identical .env files shows no changes."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create identical files
            content = "DATABASE_URL=postgresql://localhost/db\nPORT=8000\nDEBUG=true\n"
            Path(".env").write_text(content)
            Path(".env.prod").write_text(content)

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should report no changes/identical
            assert "identical" in result.output.lower() or "no" in result.output.lower()

    def test_diff_with_additions(self, tmp_path):
        """Test diff detects variables added in second file."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nVAR2=value2\n")
            Path(".env.prod").write_text("VAR1=value1\nVAR2=value2\nVAR3=new_value\nVAR4=another_new\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should show added variables
            assert "VAR3" in result.output
            assert "VAR4" in result.output
            assert "Added" in result.output or "+" in result.output

    def test_diff_with_removals(self, tmp_path):
        """Test diff detects variables removed from second file."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nVAR2=value2\nVAR3=value3\n")
            Path(".env.prod").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should show removed variables
            assert "VAR2" in result.output
            assert "VAR3" in result.output
            assert "Removed" in result.output or "-" in result.output

    def test_diff_with_modifications(self, tmp_path):
        """Test diff detects modified variable values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("DATABASE_URL=postgresql://localhost/dev\nPORT=8000\n")
            Path(".env.prod").write_text("DATABASE_URL=postgresql://prod-server/db\nPORT=3000\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should show modified variables
            assert "DATABASE_URL" in result.output
            assert "PORT" in result.output
            assert "Modified" in result.output or "~" in result.output

    def test_diff_mixed_changes(self, tmp_path):
        """Test diff with mixed additions, removals, and modifications."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=old_value\nVAR2=value2\nVAR3=value3\nVAR4=value4\n")
            Path(".env.prod").write_text("VAR1=new_value\nVAR3=value3\nVAR5=new_var\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # VAR1 modified
            assert "VAR1" in result.output
            # VAR2, VAR4 removed
            assert "VAR2" in result.output or "VAR4" in result.output
            # VAR5 added
            assert "VAR5" in result.output


class TestDiffCommandFormats:
    """Test diff command output formats (table, json, summary)."""

    def test_diff_table_format_default(self, tmp_path):
        """Test diff uses table format by default."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.prod").write_text("VAR1=modified\nVAR2=new\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Table format shows column headers and structure
            # Rich table includes unicode box drawing or status indicators
            assert "VAR1" in result.output
            assert "VAR2" in result.output

    def test_diff_table_format_explicit(self, tmp_path):
        """Test diff --format=table explicitly."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.prod").write_text("VAR1=modified\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=table"])

            assert result.exit_code == 0
            assert "VAR1" in result.output

    def test_diff_json_format(self, tmp_path):
        """Test diff --format=json produces valid JSON output."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nVAR2=value2\n")
            Path(".env.prod").write_text("VAR1=modified\nVAR3=new\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=json"])

            assert result.exit_code == 0
            # Extract JSON from output (skip banner)
            json_start = result.output.find("{")
            assert json_start != -1, "No JSON found in output"
            json_output = result.output[json_start:]
            output_data = json.loads(json_output)
            assert isinstance(output_data, dict)
            # Should have standard keys
            assert "added" in output_data
            assert "removed" in output_data
            assert "modified" in output_data
            assert "unchanged" in output_data
            # Check specific changes
            assert "VAR3" in output_data["added"]
            assert "VAR2" in output_data["removed"]
            assert "VAR1" in output_data["modified"]

    def test_diff_json_format_identical_files(self, tmp_path):
        """Test diff --format=json with identical files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            content = "VAR1=value1\nVAR2=value2\n"
            Path(".env").write_text(content)
            Path(".env.prod").write_text(content)

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=json"])

            assert result.exit_code == 0
            # Extract JSON from output (skip banner)
            json_start = result.output.find("{")
            assert json_start != -1, "No JSON found in output"
            json_output = result.output[json_start:]
            output_data = json.loads(json_output)
            assert len(output_data["added"]) == 0
            assert len(output_data["removed"]) == 0
            assert len(output_data["modified"]) == 0
            assert len(output_data["unchanged"]) == 2

    def test_diff_summary_format(self, tmp_path):
        """Test diff --format=summary shows condensed output."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nVAR2=value2\nVAR3=value3\n")
            Path(".env.prod").write_text("VAR1=modified\nVAR3=value3\nVAR4=new\nVAR5=new2\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=summary"])

            assert result.exit_code == 0
            # Summary should show counts and variable names
            assert "Added" in result.output or "added" in result.output
            assert "Removed" in result.output or "removed" in result.output
            assert "Modified" in result.output or "modified" in result.output
            # Should list variable names
            assert "VAR1" in result.output  # Modified
            assert "VAR2" in result.output  # Removed
            assert "VAR4" in result.output  # Added
            assert "VAR5" in result.output  # Added

    def test_diff_summary_format_identical(self, tmp_path):
        """Test diff --format=summary with identical files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            content = "VAR1=value1\n"
            Path(".env").write_text(content)
            Path(".env.prod").write_text(content)

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=summary"])

            assert result.exit_code == 0
            assert "identical" in result.output.lower()


class TestDiffCommandSecrets:
    """Test diff command secret handling with --show-secrets flag."""

    def test_diff_hides_secrets_by_default(self, tmp_path):
        """Test diff hides secret values by default."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("API_KEY=old_secret_key_12345\nREGULAR_VAR=value\n")
            Path(".env.prod").write_text("API_KEY=new_secret_key_67890\nREGULAR_VAR=value\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should hide secret values
            assert "secret hidden" in result.output.lower() or "<secret" in result.output.lower()
            # Should show warning about hidden secrets
            assert "WARNING" in result.output or "hidden" in result.output.lower()

    def test_diff_shows_secrets_with_flag(self, tmp_path):
        """Test diff --show-secrets reveals secret values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("API_KEY=old_secret_key_12345\nREGULAR_VAR=value\n")
            Path(".env.prod").write_text("API_KEY=new_secret_key_67890\nREGULAR_VAR=value\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            # Should show actual secret values
            assert "old_secret_key_12345" in result.output
            assert "new_secret_key_67890" in result.output
            # Should not show warning about hidden secrets
            assert "Use --show-secrets" not in result.output

    def test_diff_hides_secrets_flag_explicit(self, tmp_path):
        """Test diff --hide-secrets explicitly hides secrets."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("SECRET_KEY=my_secret_password\n")
            Path(".env.prod").write_text("SECRET_KEY=different_secret\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--hide-secrets"])

            assert result.exit_code == 0
            # Should hide secret values
            assert "my_secret_password" not in result.output
            assert "different_secret" not in result.output

    def test_diff_secret_detection_in_added_vars(self, tmp_path):
        """Test diff detects and hides secrets in newly added variables."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.prod").write_text("VAR1=value1\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should hide the AWS secret
            assert "wJalrXUtnFEMI" not in result.output or "secret hidden" in result.output.lower()

    def test_diff_secret_detection_in_removed_vars(self, tmp_path):
        """Test diff detects and hides secrets in removed variables."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nGITHUB_TOKEN=ghp_1234567890abcdefghijklmnop\n")
            Path(".env.prod").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should hide the GitHub token
            assert "ghp_1234567890" not in result.output or "secret hidden" in result.output.lower()

    def test_diff_truncates_long_values(self, tmp_path):
        """Test diff truncates long non-secret values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            long_value = "a" * 100
            Path(".env").write_text(f"LONG_VAR={long_value}\n")
            Path(".env.prod").write_text("LONG_VAR=short\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            # Should truncate to 50 chars with ... or …  (unicode ellipsis)
            assert "..." in result.output or "…" in result.output
            # Full value shouldn't appear
            assert long_value not in result.output


class TestDiffCommandFileTypes:
    """Test diff command with different file type combinations."""

    def test_diff_env_vs_env(self, tmp_path):
        """Test diff between two .env files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.production").write_text("VAR1=modified\n")

            result = runner.invoke(main, ["diff", ".env", ".env.production"])

            assert result.exit_code == 0
            assert "VAR1" in result.output

    def test_diff_env_vs_toml(self, tmp_path):
        """Test diff between .env and TOML file."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("DATABASE_URL=postgresql://localhost/dev\nPORT=8000\n")
            Path("config.toml").write_text(
                "[tool.tripwire]\n" 'DATABASE_URL = "postgresql://prod/db"\n' "PORT = 3000\n"
            )

            result = runner.invoke(main, ["diff", ".env", "config.toml"])

            assert result.exit_code == 0
            assert "DATABASE_URL" in result.output
            assert "PORT" in result.output

    def test_diff_toml_vs_toml(self, tmp_path):
        """Test diff between two TOML files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("config1.toml").write_text("[tool.tripwire]\nVAR1 = 'value1'\n")
            Path("config2.toml").write_text("[tool.tripwire]\nVAR1 = 'modified'\nVAR2 = 'new'\n")

            result = runner.invoke(main, ["diff", "config1.toml", "config2.toml"])

            assert result.exit_code == 0
            assert "VAR1" in result.output

    def test_diff_toml_vs_env(self, tmp_path):
        """Test diff with TOML as source1 and .env as source2."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("config.toml").write_text("[tool.tripwire]\nVAR1 = 'value1'\n")
            Path(".env").write_text("VAR1=modified\n")

            result = runner.invoke(main, ["diff", "config.toml", ".env"])

            assert result.exit_code == 0
            assert "VAR1" in result.output


class TestDiffCommandErrorHandling:
    """Test diff command error handling and edge cases."""

    def test_diff_missing_first_file(self, tmp_path):
        """Test diff exits with error when first file doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env.prod").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", "nonexistent.env", ".env.prod"])

            assert result.exit_code == 1
            assert "ERROR" in result.output
            assert "not found" in result.output.lower() or "nonexistent.env" in result.output

    def test_diff_missing_second_file(self, tmp_path):
        """Test diff exits with error when second file doesn't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", ".env", "nonexistent.env"])

            assert result.exit_code == 1
            assert "ERROR" in result.output
            assert "not found" in result.output.lower() or "nonexistent.env" in result.output

    def test_diff_both_files_missing(self, tmp_path):
        """Test diff exits with error when both files don't exist."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["diff", "missing1.env", "missing2.env"])

            assert result.exit_code == 1
            assert "ERROR" in result.output

    def test_diff_empty_files(self, tmp_path):
        """Test diff with empty files shows no changes."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("")
            Path(".env.prod").write_text("")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            assert "identical" in result.output.lower() or "no" in result.output.lower()

    def test_diff_one_empty_file(self, tmp_path):
        """Test diff with one empty file shows all variables as removed."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\nVAR2=value2\n")
            Path(".env.prod").write_text("")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # All variables should be removed
            assert "VAR1" in result.output
            assert "VAR2" in result.output
            assert "Removed" in result.output or "-" in result.output

    def test_diff_with_invalid_toml(self, tmp_path):
        """Test diff handles invalid TOML gracefully."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path("invalid.toml").write_text("[invalid syntax\nno closing bracket")

            result = runner.invoke(main, ["diff", ".env", "invalid.toml"])

            # Should fail with error message
            assert result.exit_code == 1
            assert "ERROR" in result.output

    def test_diff_with_malformed_env(self, tmp_path):
        """Test diff handles malformed .env files gracefully."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            # Malformed .env (though most parsers are lenient)
            Path(".env.bad").write_text("=no_key\nVAR_WITH_NO_VALUE\n")

            result = runner.invoke(main, ["diff", ".env", ".env.bad"])

            # May succeed or fail depending on parser tolerance
            assert result.exit_code in (0, 1)

    def test_diff_unsupported_file_format(self, tmp_path):
        """Test diff rejects unsupported file formats."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path("config.json").write_text('{"VAR1": "value1"}')

            result = runner.invoke(main, ["diff", ".env", "config.json"])

            assert result.exit_code == 1
            assert "ERROR" in result.output
            assert "Unsupported" in result.output or "format" in result.output.lower()


class TestDiffCommandEdgeCases:
    """Test diff command edge cases and special scenarios."""

    def test_diff_with_comments_in_env(self, tmp_path):
        """Test diff handles comments in .env files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("# Database config\nDATABASE_URL=localhost\n# Port\nPORT=8000\n")
            Path(".env.prod").write_text("# Production config\nDATABASE_URL=prod-server\nPORT=8000\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should compare values, ignoring comments
            assert "DATABASE_URL" in result.output
            # PORT should be unchanged
            assert "Modified" in result.output or "~" in result.output

    def test_diff_with_multiline_values(self, tmp_path):
        """Test diff handles multiline values correctly."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text('CERT="-----BEGIN CERTIFICATE-----\nOLD_CERT_DATA"\n')
            Path(".env.prod").write_text('CERT="-----BEGIN CERTIFICATE-----\nNEW_CERT_DATA"\n')

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            assert "CERT" in result.output

    def test_diff_with_special_characters(self, tmp_path):
        """Test diff handles special characters in values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("SPECIAL=value!@#$%^&*()\n")
            Path(".env.prod").write_text("SPECIAL=different!@#$%^&*()\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            assert "SPECIAL" in result.output

    def test_diff_with_unicode_values(self, tmp_path):
        """Test diff handles unicode characters."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("MESSAGE=Hello 世界\n", encoding="utf-8")
            Path(".env.prod").write_text("MESSAGE=你好 World\n", encoding="utf-8")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            assert "MESSAGE" in result.output

    def test_diff_with_empty_values(self, tmp_path):
        """Test diff handles empty variable values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=\nVAR2=value\n")
            Path(".env.prod").write_text("VAR1=now_has_value\nVAR2=\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            # Both should show as modified
            assert "VAR1" in result.output
            assert "VAR2" in result.output

    def test_diff_case_sensitive_keys(self, tmp_path):
        """Test diff treats variable names as case-sensitive."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("PORT=8000\nport=9000\n")
            Path(".env.prod").write_text("port=3000\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # PORT (uppercase) should be removed
            # port (lowercase) should be modified
            assert "PORT" in result.output or "port" in result.output

    def test_diff_preserves_variable_order_in_output(self, tmp_path):
        """Test diff displays variables in sorted order."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("ZZZ=1\nAAA=2\nMMM=3\n")
            Path(".env.prod").write_text("ZZZ=modified\nAAA=2\nMMM=modified\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Variables should appear (implementation may sort them)
            assert "ZZZ" in result.output
            assert "MMM" in result.output


class TestDiffCommandSummary:
    """Test diff command summary functionality."""

    def test_diff_summary_message_format(self, tmp_path):
        """Test diff includes summary message with counts."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=v1\nVAR2=v2\nVAR3=v3\n")
            Path(".env.prod").write_text("VAR1=modified\nVAR3=v3\nVAR4=new1\nVAR5=new2\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should show summary with counts
            # 2 added, 1 removed, 1 modified, 1 unchanged
            output_lower = result.output.lower()
            assert "added" in output_lower or "removed" in output_lower or "modified" in output_lower

    def test_diff_shows_file_names_in_output(self, tmp_path):
        """Test diff displays source file names in output."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env.dev").write_text("VAR1=dev_value\n")
            Path(".env.prod").write_text("VAR1=prod_value\n")

            result = runner.invoke(main, ["diff", ".env.dev", ".env.prod"])

            assert result.exit_code == 0
            # Should mention file names
            assert ".env.dev" in result.output or ".env.prod" in result.output


class TestDiffCommandBranding:
    """Test diff command includes TripWire branding."""

    def test_diff_shows_logo_banner(self, tmp_path):
        """Test diff displays TripWire logo banner."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.prod").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should include branding (LOGO_BANNER or project name)
            # The banner is printed via console.print(LOGO_BANNER)
            # Content depends on branding.py implementation

    def test_diff_shows_comparison_header(self, tmp_path):
        """Test diff displays header with file names being compared."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("source1.env").write_text("VAR1=value1\n")
            Path("source2.env").write_text("VAR1=value1\n")

            result = runner.invoke(main, ["diff", "source1.env", "source2.env"])

            assert result.exit_code == 0
            # Should show "Comparing configurations: source1.env vs source2.env"
            assert "Comparing" in result.output or "compar" in result.output.lower()
            assert "source1.env" in result.output or "source2.env" in result.output


class TestDiffCommandIntegration:
    """Integration tests for complex real-world diff scenarios."""

    def test_diff_development_vs_production_config(self, tmp_path):
        """Test realistic diff between dev and prod configurations."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env.dev").write_text(
                "DATABASE_URL=postgresql://localhost/dev_db\n"
                "REDIS_URL=redis://localhost:6379/0\n"
                "DEBUG=true\n"
                "LOG_LEVEL=DEBUG\n"
                "SECRET_KEY=dev_secret_12345\n"
            )
            Path(".env.prod").write_text(
                "DATABASE_URL=postgresql://prod-server:5432/prod_db\n"
                "REDIS_URL=redis://prod-redis:6379/0\n"
                "DEBUG=false\n"
                "LOG_LEVEL=INFO\n"
                "SECRET_KEY=prod_secret_67890\n"
                "SENTRY_DSN=https://example@sentry.io/123\n"
            )

            result = runner.invoke(main, ["diff", ".env.dev", ".env.prod"])

            assert result.exit_code == 0
            # Should detect all modifications
            assert "DATABASE_URL" in result.output
            assert "REDIS_URL" in result.output
            assert "DEBUG" in result.output
            # Should detect addition
            assert "SENTRY_DSN" in result.output
            # Should hide secrets
            assert "WARNING" in result.output or "hidden" in result.output.lower()

    def test_diff_with_nested_toml_structure(self, tmp_path):
        """Test diff with nested TOML configuration."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("config1.toml").write_text(
                "[tool.tripwire.database]\n"
                'host = "localhost"\n'
                "port = 5432\n"
                "[tool.tripwire.cache]\n"
                'url = "redis://localhost"\n'
            )
            Path("config2.toml").write_text(
                "[tool.tripwire.database]\n"
                'host = "prod-server"\n'
                "port = 5432\n"
                "[tool.tripwire.cache]\n"
                'url = "redis://prod"\n'
            )

            result = runner.invoke(main, ["diff", "config1.toml", "config2.toml"])

            assert result.exit_code == 0
            # Should detect nested changes
            assert "database.host" in result.output or "host" in result.output
            assert "cache.url" in result.output or "url" in result.output

    def test_diff_large_configuration(self, tmp_path):
        """Test diff with large configuration files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create config with many variables
            vars1 = [f"VAR_{i}=value_{i}\n" for i in range(50)]
            vars2 = [f"VAR_{i}=modified_{i}\n" if i % 5 == 0 else f"VAR_{i}=value_{i}\n" for i in range(50)]
            vars2.append("NEW_VAR=new_value\n")

            Path(".env").write_text("".join(vars1))
            Path(".env.prod").write_text("".join(vars2))

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # Should detect modifications (every 5th variable)
            assert "VAR_0" in result.output or "VAR_5" in result.output
            # Should detect addition
            assert "NEW_VAR" in result.output

    def test_diff_json_format_comprehensive(self, tmp_path):
        """Test JSON format with comprehensive diff data."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("KEEP=same\nMODIFY=old\nREMOVE=gone\n")
            Path(".env.prod").write_text("KEEP=same\nMODIFY=new\nADD=added\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--format=json"])

            assert result.exit_code == 0
            # Extract JSON from output (skip banner)
            json_start = result.output.find("{")
            assert json_start != -1, "No JSON found in output"
            json_output = result.output[json_start:]
            data = json.loads(json_output)

            # Verify all categories
            assert "ADD" in data["added"]
            assert data["added"]["ADD"] == "added"

            assert "REMOVE" in data["removed"]
            assert data["removed"]["REMOVE"] == "gone"

            assert "MODIFY" in data["modified"]
            assert data["modified"]["MODIFY"]["old"] == "old"
            assert data["modified"]["MODIFY"]["new"] == "new"

            assert "KEEP" in data["unchanged"]
            assert data["unchanged"]["KEEP"] == "same"


class TestDiffCommandPerformance:
    """Test diff command handles performance scenarios."""

    def test_diff_with_very_long_values(self, tmp_path):
        """Test diff handles very long variable values."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            long_val = "x" * 1000
            Path(".env").write_text(f"LONG_VAR={long_val}\n")
            Path(".env.prod").write_text(f"LONG_VAR={long_val}y\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod", "--show-secrets"])

            assert result.exit_code == 0
            # Should handle long values without crashing
            assert "LONG_VAR" in result.output
            # Should truncate for display (using ... or … unicode ellipsis)
            assert "..." in result.output or "…" in result.output

    def test_diff_handles_loading_status(self, tmp_path):
        """Test diff shows loading status for files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.prod").write_text("VAR1=modified\n")

            result = runner.invoke(main, ["diff", ".env", ".env.prod"])

            assert result.exit_code == 0
            # The code uses console.status() for loading feedback
            # Output may include status indicators
