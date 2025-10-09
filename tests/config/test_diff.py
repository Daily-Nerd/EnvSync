"""Integration tests for configuration diff functionality."""

import pytest

from tripwire.config.repository import ConfigRepository


class TestConfigDiff:
    """Integration tests for diff functionality across formats."""

    def test_diff_env_vs_toml(self, tmp_path):
        """Test diff between .env and TOML sources."""
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://localhost/dev\n" "PORT=8000\n" "DEBUG=true\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            "[tool.tripwire]\n" 'DATABASE_URL = "postgresql://localhost/prod"\n' "PORT = 3000\n" 'NEW_VAR = "value"\n'
        )

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # NEW_VAR added in TOML
        assert "NEW_VAR" in diff.added
        assert diff.added["NEW_VAR"].value == "value"

        # DEBUG removed in TOML
        assert "DEBUG" in diff.removed
        assert diff.removed["DEBUG"].value == "true"

        # DATABASE_URL and PORT modified
        assert "DATABASE_URL" in diff.modified
        old_db, new_db = diff.modified["DATABASE_URL"]
        assert "dev" in old_db.value
        assert "prod" in new_db.value

        assert "PORT" in diff.modified
        old_port, new_port = diff.modified["PORT"]
        assert old_port.value == "8000"
        assert new_port.value == 3000  # TOML preserves int type

    def test_diff_with_nested_toml(self, tmp_path):
        """Test diff with nested TOML structure."""
        env_file = tmp_path / ".env"
        env_file.write_text("database.host=localhost\n" "database.port=5432\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire.database]\n" 'host = "db.example.com"\n' "port = 5432\n")

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # database.host modified
        assert "database.host" in diff.modified
        old_host, new_host = diff.modified["database.host"]
        assert old_host.value == "localhost"
        assert new_host.value == "db.example.com"

        # database.port unchanged
        assert "database.port" in diff.unchanged

    def test_diff_summary_formatting(self, tmp_path):
        """Test diff summary produces readable output."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\nVAR2=value2\nVAR3=value3\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text(
            "[tool.tripwire]\n" 'VAR1 = "modified"\n' 'VAR3 = "value3"\n' 'VAR4 = "new"\n' 'VAR5 = "new"\n'
        )

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        summary = diff.summary()

        # Should mention all change types
        assert "added" in summary
        assert "removed" in summary
        assert "modified" in summary

        # Should have correct counts
        assert "2 added" in summary  # VAR4, VAR5
        assert "1 removed" in summary  # VAR2
        assert "1 modified" in summary  # VAR1

    def test_diff_case_sensitivity(self, tmp_path):
        """Test diff is case-sensitive for keys."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nport=9000\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 3000\n")

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # PORT (uppercase) should be removed
        assert "PORT" in diff.removed

        # port (lowercase) should be modified
        assert "port" in diff.modified

    def test_diff_with_secrets(self, tmp_path):
        """Test diff preserves secret detection metadata."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=old_secret\nREGULAR_VAR=value\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\n" 'API_KEY = "new_secret"\n' 'REGULAR_VAR = "value"\n')

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # API_KEY should be modified and marked as secret
        assert "API_KEY" in diff.modified
        old_key, new_key = diff.modified["API_KEY"]
        assert old_key.metadata.is_secret is True
        assert new_key.metadata.is_secret is True

        # REGULAR_VAR should not be marked as secret
        assert "REGULAR_VAR" in diff.unchanged
        assert diff.unchanged["REGULAR_VAR"].metadata.is_secret is False

    def test_diff_empty_repos(self, tmp_path):
        """Test diff with empty repositories."""
        env_file1 = tmp_path / ".env"
        env_file1.write_text("")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("")

        repo1 = ConfigRepository.from_file(env_file1).load()
        repo2 = ConfigRepository.from_file(env_file2).load()

        diff = repo1.diff(repo2)

        assert not diff.has_changes
        assert diff.summary() == "No differences"

    def test_diff_completely_different(self, tmp_path):
        """Test diff with completely different configurations."""
        env_file = tmp_path / ".env"
        env_file.write_text("VAR1=value1\nVAR2=value2\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nVAR3 = 3\nVAR4 = 4\n")

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # All vars from env should be removed
        assert "VAR1" in diff.removed
        assert "VAR2" in diff.removed

        # All vars from toml should be added
        assert "VAR3" in diff.added
        assert "VAR4" in diff.added

        # No modified or unchanged
        assert len(diff.modified) == 0
        assert len(diff.unchanged) == 0

    def test_diff_type_changes(self, tmp_path):
        """Test diff compares raw_value strings, not types.

        Note: Diff compares raw_value (string representation), so values with
        different types but identical string representations are considered unchanged.
        This is intentional - the diff tool is for detecting configuration drift,
        not type differences.
        """
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nDEBUG=true\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nPORT = 8000\nDEBUG = true\n")

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # Values stringify to the same thing, so they're considered unchanged
        # Even though types differ: "8000" (str) vs 8000 (int), "true" (str) vs true (bool)
        assert "PORT" in diff.unchanged
        assert "DEBUG" in diff.unchanged

        # Verify the actual values have different types
        env_port = repo_env.get("PORT")
        toml_port = repo_toml.get("PORT")
        assert env_port.value == "8000"  # str
        assert toml_port.value == 8000  # int
        assert env_port.raw_value == toml_port.raw_value  # Both "8000"

    def test_diff_multiline_values(self, tmp_path):
        """Test diff with multiline values."""
        env_file = tmp_path / ".env"
        env_file.write_text('CERTIFICATE="-----BEGIN CERTIFICATE-----\nABC123"\n')

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\n" 'CERTIFICATE = """-----BEGIN CERTIFICATE-----\nXYZ789"""\n')

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        # Should detect modification
        assert "CERTIFICATE" in diff.modified

    def test_diff_preserves_source_metadata(self, tmp_path):
        """Test diff preserves source metadata from both sides."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nPORT = 3000\n")

        repo_env = ConfigRepository.from_file(env_file).load()
        repo_toml = ConfigRepository.from_file(toml_file).load()

        diff = repo_env.diff(repo_toml)

        old_port, new_port = diff.modified["PORT"]

        # Old value should have .env metadata
        assert old_port.metadata.source_type.value == "env"
        assert old_port.metadata.file_path == env_file
        assert old_port.metadata.line_number == 1

        # New value should have TOML metadata
        assert new_port.metadata.source_type.value == "toml"
        assert new_port.metadata.file_path == toml_file
