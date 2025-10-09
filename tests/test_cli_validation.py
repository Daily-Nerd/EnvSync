"""Comprehensive CLI validation tests.

These tests ensure CLI commands work correctly across all scenarios.
Workflows should rely on these tests rather than reimplementing validation.

Testing Philosophy:
- Test BEHAVIORS, not implementation details
- Test STRUCTURE, not exact wording
- Test CAPABILITIES, not appearance
- Use flexible assertions that tolerate cosmetic changes
"""

import json
import re
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from tripwire.cli import main


class TestCLIBasics:
    """Test basic CLI functionality and entry point."""

    def test_cli_entry_point_exists(self):
        """Test that tripwire command is available via Click."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, "CLI entry point should execute successfully"

    def test_version_flag_works(self):
        """Test --version flag returns version information."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0, "Version flag should execute successfully"
        # Flexible: just check version format exists (semantic versioning)
        assert re.search(r"\d+\.\d+\.\d+", result.output), "Version output should contain semver format"

    def test_help_flag_works(self):
        """Test --help flag returns help information."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, "Help flag should execute successfully"

    def test_help_short_flag_works(self):
        """Test -h short flag works as alias for --help."""
        runner = CliRunner()
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0, "Short help flag should work"

    def test_help_output_structure(self):
        """Test help output has expected structure (not exact text).

        This test validates structure, not specific wording.
        Tests should pass even if help text is reworded.
        """
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

        # Test structural elements (case-insensitive, flexible)
        output_lower = result.output.lower()
        assert "usage:" in output_lower, "Help should show usage information"
        assert "options:" in output_lower, "Help should show options section"
        assert "tripwire" in output_lower, "Help should mention program name"

    def test_help_output_not_empty(self):
        """Test help output produces non-empty content."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert len(result.output) > 100, "Help should provide substantial information"

    def test_invalid_command_shows_error(self):
        """Test invalid commands produce appropriate error."""
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent_command_xyz"])
        assert result.exit_code != 0, "Invalid command should fail"
        # Error message should be somewhat helpful
        assert len(result.output) > 0, "Should provide error message"

    def test_cli_does_not_crash_on_empty_args(self):
        """Test CLI handles no arguments gracefully."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        # Should show help or handle gracefully (not crash)
        assert result.exit_code in (0, 2), "Should handle empty args gracefully"


class TestVersionConsistency:
    """Test version is consistent across all sources."""

    def test_version_in_cli_matches_package(self):
        """Test CLI --version matches package __version__.

        This ensures the version is synchronized across:
        - src/tripwire/__init__.py
        - src/tripwire/cli.py
        - pyproject.toml
        """
        import tripwire

        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0

        # Extract version from output (flexible regex for various formats)
        match = re.search(r"(\d+\.\d+\.\d+(?:-[\w.]+)?)", result.output)
        assert match, "Should find version in --version output"
        cli_version = match.group(1)

        assert (
            cli_version == tripwire.__version__
        ), f"CLI version {cli_version} should match package version {tripwire.__version__}"

    def test_version_format_is_valid_semver(self):
        """Test version follows semantic versioning (semver).

        Valid formats:
        - 1.2.3 (release)
        - 1.2.3-rc1 (release candidate)
        - 1.2.3-beta.2 (beta)
        - 1.2.3-alpha (alpha)
        """
        import tripwire

        # Regex for semver with optional prerelease
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?$"
        assert re.match(
            semver_pattern, tripwire.__version__
        ), f"Version {tripwire.__version__} should follow semver format"

    def test_version_output_is_consistent(self):
        """Test --version produces same output when called multiple times."""
        runner = CliRunner()

        # Call multiple times
        results = [runner.invoke(main, ["--version"]) for _ in range(3)]

        # All should succeed
        for result in results:
            assert result.exit_code == 0

        # All should produce identical output
        outputs = [r.output for r in results]
        assert len(set(outputs)) == 1, "Version output should be deterministic"


class TestCommandAvailability:
    """Test all expected commands are available and executable."""

    # All CLI commands that should be available
    EXPECTED_COMMANDS = [
        "init",
        "generate",
        "check",
        "sync",
        "scan",
        "audit",
        "validate",
        "docs",
    ]

    @pytest.mark.parametrize("command", EXPECTED_COMMANDS)
    def test_all_commands_have_help(self, command):
        """Test that all commands have working --help flag.

        This validates:
        1. Command is registered
        2. Command can execute
        3. Help system works
        """
        runner = CliRunner()
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0, f"{command} --help should work"
        assert len(result.output) > 0, f"{command} should provide help text"

    @pytest.mark.parametrize("command", EXPECTED_COMMANDS)
    def test_command_help_has_usage_section(self, command):
        """Test command help includes usage information."""
        runner = CliRunner()
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output, f"{command} help should show usage"

    @pytest.mark.parametrize(
        "command,expected_keywords",
        [
            ("init", ["project", "env", "create", "initialize"]),
            ("generate", ["example", "scan", "code", "file"]),
            ("check", ["drift", "missing", "compare", "env"]),
            ("sync", ["synchronize", "merge", "update", "env"]),
            ("scan", ["secrets", "git", "detect", "security"]),
            ("audit", ["leak", "history", "git", "secret"]),
            ("validate", ["environment", "variable", "check"]),
            ("docs", ["documentation", "generate", "format"]),
        ],
    )
    def test_command_help_contains_relevant_keywords(self, command, expected_keywords):
        """Test command help contains relevant keywords (not exact text).

        This test is flexible - it only checks that SOME relevant keywords
        appear, not exact wording. Helps text can be reworded without
        breaking tests.
        """
        runner = CliRunner()
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0

        # At least one keyword should appear (case-insensitive)
        output_lower = result.output.lower()
        found = any(kw.lower() in output_lower for kw in expected_keywords)
        assert found, f"None of {expected_keywords} found in help for '{command}' command"

    def test_all_commands_listed_in_main_help(self):
        """Test main help lists all available commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0

        output_lower = result.output.lower()

        # Check each command appears in main help
        for command in self.EXPECTED_COMMANDS:
            assert command in output_lower, f"Command '{command}' should appear in main help"


class TestCLIBehavior:
    """Test CLI behavior and functionality (smoke tests)."""

    def test_init_creates_required_files(self, tmp_path):
        """Test init command creates expected files.

        Tests BEHAVIOR (files created), not output text.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--project-type=cli"])

            # Should succeed
            assert result.exit_code == 0, "init should succeed"

            # Should create files (behavior test)
            assert Path(".env").exists(), "init should create .env"
            assert Path(".env.example").exists(), "init should create .env.example"

            # Files should have content
            assert Path(".env").stat().st_size > 0, ".env should not be empty"
            assert Path(".env.example").stat().st_size > 0, ".env.example should not be empty"

    @pytest.mark.parametrize("project_type", ["web", "cli", "data", "other"])
    def test_init_supports_all_project_types(self, tmp_path, project_type):
        """Test init works with all project type options."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", f"--project-type={project_type}"])
            assert result.exit_code == 0, f"init should work with type={project_type}"
            assert Path(".env").exists(), "Should create .env"

    def test_init_updates_gitignore(self, tmp_path):
        """Test init creates or updates .gitignore."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--project-type=cli"])
            assert result.exit_code == 0

            # Should create/update .gitignore
            assert Path(".gitignore").exists(), "Should create .gitignore"

            # Should contain .env entries
            gitignore_content = Path(".gitignore").read_text()
            assert ".env" in gitignore_content, ".gitignore should protect .env"

    def test_generate_requires_code_files(self, tmp_path):
        """Test generate command handles no code gracefully."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # No Python files with env usage
            result = runner.invoke(main, ["generate"])

            # Should fail gracefully (exit code 1, not crash)
            assert result.exit_code == 1, "Should exit with error when no env vars found"

            # Should provide informative message
            output_lower = result.output.lower()
            assert (
                "no environment variables" in output_lower or "not found" in output_lower
            ), "Should explain why it failed"

    def test_generate_creates_example_file(self, tmp_path):
        """Test generate creates .env.example from code."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create Python file with env usage
            Path("app.py").write_text(
                """
from tripwire import env
API_KEY = env.require('API_KEY')
"""
            )

            result = runner.invoke(main, ["generate"])
            assert result.exit_code == 0, "generate should succeed"
            assert Path(".env.example").exists(), "Should create .env.example"

            # Should contain the variable
            content = Path(".env.example").read_text()
            assert "API_KEY" in content, "Should include discovered variables"

    def test_check_compares_env_files(self, tmp_path):
        """Test check command compares .env and .env.example."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create test files
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.example").write_text("VAR1=\nVAR2=\n")

            result = runner.invoke(main, ["check"])
            assert result.exit_code == 0, "check should execute successfully"

            # Should detect drift (VAR2 missing)
            assert "VAR2" in result.output, "Should report missing variable"

    def test_commands_with_json_output_produce_valid_json(self, tmp_path):
        """Test commands with --json flag produce parseable JSON.

        This validates STRUCTURE, not specific content.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create test files
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.example").write_text("VAR1=\nVAR2=\n")

            result = runner.invoke(main, ["check", "--json"])
            assert result.exit_code == 0, "check --json should succeed"

            # Test it's valid JSON (don't care about exact structure)
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict), "JSON output should be a dictionary"
            except json.JSONDecodeError:
                pytest.fail("Command should produce valid JSON output")


class TestCLIErrorHandling:
    """Test CLI handles errors gracefully."""

    def test_missing_env_file_shows_helpful_error(self, tmp_path):
        """Test commands show helpful errors for missing files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create only .env.example (missing .env)
            Path(".env.example").write_text("VAR1=\n")

            result = runner.invoke(main, ["check"])

            # Should provide helpful error message
            output_lower = result.output.lower()
            assert "not found" in output_lower or "does not exist" in output_lower, "Should indicate file is missing"

    def test_invalid_project_type_shows_error(self, tmp_path):
        """Test init with invalid project type shows helpful error."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--project-type=invalid_xyz"])

            # Should fail with helpful message
            assert result.exit_code != 0, "Should reject invalid project type"
            # Click shows choices in error
            output_lower = result.output.lower()
            assert "invalid" in output_lower or "choice" in output_lower, "Should explain valid choices"

    def test_missing_required_argument_shows_usage(self, tmp_path):
        """Test commands requiring arguments show usage when missing."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # audit requires secret name or --all flag
            result = runner.invoke(main, ["audit"])

            # Should fail with helpful message
            assert result.exit_code != 0, "Should require arguments"
            assert len(result.output) > 0, "Should provide error message"

    def test_conflicting_flags_handled_gracefully(self, tmp_path):
        """Test conflicting flags produce clear error."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # audit --all and SECRET_NAME are conflicting
            result = runner.invoke(main, ["audit", "SECRET_KEY", "--all"])

            # Should fail with clear error
            assert result.exit_code != 0, "Should reject conflicting flags"
            output_lower = result.output.lower()
            assert "error" in output_lower or "cannot" in output_lower, "Should explain the conflict"


class TestCLIPerformance:
    """Test CLI performance characteristics."""

    def test_help_commands_are_fast(self):
        """Test help commands execute quickly (< 2 seconds).

        Help should be nearly instant, even on slow systems.
        Using 2s threshold to be generous for CI environments.
        """
        runner = CliRunner()

        start = time.time()
        result = runner.invoke(main, ["--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0, "Help should succeed"
        assert elapsed < 2.0, f"Help took {elapsed:.2f}s (should be < 2s)"

    @pytest.mark.parametrize("command", ["init", "generate", "check", "sync", "validate", "docs"])
    def test_command_help_is_fast(self, command):
        """Test individual command help is fast.

        Each command's help should load quickly.
        """
        runner = CliRunner()

        start = time.time()
        result = runner.invoke(main, [command, "--help"])
        elapsed = time.time() - start

        assert result.exit_code == 0, f"{command} --help should succeed"
        assert elapsed < 2.0, f"{command} --help took {elapsed:.2f}s (should be < 2s)"

    def test_version_is_fast(self):
        """Test --version is fast (should be instant)."""
        runner = CliRunner()

        start = time.time()
        result = runner.invoke(main, ["--version"])
        elapsed = time.time() - start

        assert result.exit_code == 0, "Version should succeed"
        assert elapsed < 1.0, f"Version took {elapsed:.2f}s (should be < 1s)"


class TestCLIOutputFormats:
    """Test CLI supports different output formats."""

    def test_check_supports_json_output(self, tmp_path):
        """Test check command --json flag."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.example").write_text("VAR1=\n")

            result = runner.invoke(main, ["check", "--json"])
            assert result.exit_code == 0, "check --json should work"

            # Should produce valid JSON
            data = json.loads(result.output)
            assert "status" in data or "missing" in data, "JSON should have expected structure"

    def test_audit_supports_json_output(self, tmp_path):
        """Test audit command --json flag."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize git repo (audit requires it)
            import subprocess

            subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True)

            # Create .env file
            Path(".env").write_text("API_KEY=test123\n")

            result = runner.invoke(main, ["audit", "--all", "--json"])

            # Should produce JSON (even if no leaks found)
            if result.exit_code == 0:
                try:
                    data = json.loads(result.output)
                    assert isinstance(data, dict), "Should produce JSON dict"
                except json.JSONDecodeError:
                    pytest.fail("audit --json should produce valid JSON")

    @pytest.mark.parametrize("format_type", ["markdown", "html", "json"])
    def test_docs_supports_all_formats(self, tmp_path, format_type):
        """Test docs command supports all format options."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create Python file with env usage
            Path("app.py").write_text(
                """
from tripwire import env
API_KEY = env.require('API_KEY')
"""
            )

            result = runner.invoke(main, ["docs", f"--format={format_type}"])

            # Some formats may not work without env vars, but command should execute
            # (exit code 0 or 1 both acceptable depending on content)
            assert result.exit_code in (0, 1), f"docs --format={format_type} should execute"


class TestCLIFlags:
    """Test CLI flags and options work correctly."""

    def test_strict_flag_affects_exit_code(self, tmp_path):
        """Test --strict flag causes non-zero exit on issues."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create files with drift
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.example").write_text("VAR1=\nVAR2=\n")

            # Without --strict: should succeed
            result = runner.invoke(main, ["check"])
            assert result.exit_code == 0, "check without --strict should succeed"

            # With --strict: should fail due to missing VAR2
            result = runner.invoke(main, ["check", "--strict"])
            assert result.exit_code == 1, "check --strict should fail on drift"

    def test_dry_run_flag_prevents_changes(self, tmp_path):
        """Test --dry-run flag prevents file modifications."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create files
            Path(".env").write_text("VAR1=value1\n")
            Path(".env.example").write_text("VAR1=\nVAR2=default2\n")

            original_content = Path(".env").read_text()

            # Run sync with --dry-run
            result = runner.invoke(main, ["sync", "--dry-run"])
            assert result.exit_code == 0, "sync --dry-run should succeed"

            # File should not be modified
            assert Path(".env").read_text() == original_content, "Dry run should not modify files"

            # Output should indicate dry run
            assert "dry run" in result.output.lower(), "Should indicate dry run mode"

    def test_force_flag_allows_overwrite(self, tmp_path):
        """Test --force flag allows overwriting existing files."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .env.example
            Path(".env.example").write_text("OLD_CONTENT=value\n")

            # Create Python file
            Path("app.py").write_text(
                """
from tripwire import env
NEW_VAR = env.require('NEW_VAR')
"""
            )

            # Without --force: should fail
            result = runner.invoke(main, ["generate"])
            assert result.exit_code == 1, "generate should fail without --force"

            # With --force: should succeed
            result = runner.invoke(main, ["generate", "--force"])
            assert result.exit_code == 0, "generate --force should succeed"

            # File should be updated
            content = Path(".env.example").read_text()
            assert "NEW_VAR" in content, "Should generate new content"


class TestCLIIntegration:
    """Test full CLI workflow integration."""

    def test_complete_workflow_from_init_to_validate(self, tmp_path):
        """Test complete workflow: init → code → generate → validate.

        This is an end-to-end smoke test of the most common workflow.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Step 1: Initialize project
            result = runner.invoke(main, ["init", "--project-type=cli"])
            assert result.exit_code == 0, "init should succeed"
            assert Path(".env").exists(), "init should create .env"

            # Step 2: Create application code
            Path("app.py").write_text(
                """
from tripwire import env

API_KEY = env.require('API_KEY', description='API key')
DEBUG = env.optional('DEBUG', default=False, type=bool)
"""
            )

            # Step 3: Generate .env.example from code
            result = runner.invoke(main, ["generate", "--force"])
            assert result.exit_code == 0, "generate should succeed"

            # Step 4: Add required values to .env
            env_content = Path(".env").read_text()
            env_content += "\nAPI_KEY=test_api_key_12345"
            Path(".env").write_text(env_content)

            # Step 5: Validate everything is set
            result = runner.invoke(main, ["validate"])
            assert result.exit_code == 0, "validate should succeed"

            # Workflow should complete successfully
            # If we got here, all steps worked!


class TestCLIRichOutput:
    """Test Rich library integration for formatted output."""

    def test_cli_handles_unicode_output(self, tmp_path):
        """Test CLI properly handles Unicode characters in output.

        TripWire uses Rich for formatted output with emojis and symbols.
        This test ensures Unicode handling works.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--project-type=cli"])

            # Should succeed without Unicode errors
            assert result.exit_code == 0, "Should handle Unicode in output"

            # Output should not have encoding errors
            assert "\\x" not in result.output, "Should not have escaped Unicode"

    def test_cli_output_is_readable(self, tmp_path):
        """Test CLI produces human-readable output."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["--help"])

            # Should produce readable ASCII/UTF-8 text
            assert result.output.isprintable() or "\n" in result.output, "Output should be printable text"


# Mark slow tests for optional skipping
class TestCLISlow:
    """Slow tests that can be skipped with pytest -m 'not slow'."""

    @pytest.mark.slow
    def test_scan_command_with_git_history(self, tmp_path):
        """Test scan command with git repository (slow).

        This test requires git initialization and can be slow.
        """
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize git
            import subprocess

            subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)

            # Create .env
            Path(".env").write_text("API_KEY=test123\n")

            result = runner.invoke(main, ["scan"])

            # Should execute (may or may not find secrets)
            assert result.exit_code in (0, 1), "scan should execute"

    @pytest.mark.slow
    def test_audit_command_with_git_history(self, tmp_path):
        """Test audit command with git repository (slow)."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize git
            import subprocess

            subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, capture_output=True)

            # Create .env and commit
            Path(".env").write_text("SECRET_KEY=abc123\n")

            result = runner.invoke(main, ["audit", "--all"])

            # Should execute (may or may not find leaks)
            assert result.exit_code in (0, 1), "audit should execute"
