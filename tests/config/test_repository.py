"""Tests for ConfigRepository facade."""

from pathlib import Path

import pytest

from tripwire.config.models import ConfigFormat, ConfigValue, SourceMetadata
from tripwire.config.repository import ConfigRepository, MergeStrategy
from tripwire.config.sources.env_file import EnvFileSource
from tripwire.config.sources.toml_source import TOMLSource


class TestConfigRepository:
    """Tests for ConfigRepository facade."""

    def test_empty_repository(self):
        """Test creating empty repository."""
        repo = ConfigRepository()

        assert repo.sources == []
        assert repo._config is None

    def test_add_source_builder_pattern(self, tmp_path):
        """Test add_source returns self for chaining."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        repo = ConfigRepository()
        result = repo.add_source(EnvFileSource(env_file))

        assert result is repo
        assert len(repo.sources) == 1

    def test_load_single_source(self, tmp_path):
        """Test loading from single source."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        repo = ConfigRepository()
        repo.add_source(EnvFileSource(env_file))
        repo.load()

        assert repo.get("PORT").value == "8000"
        assert repo.get("HOST").value == "localhost"

    def test_load_multiple_sources_last_wins(self, tmp_path):
        """Test loading from multiple sources with last wins strategy."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 3000\n")

        repo = ConfigRepository(merge_strategy=MergeStrategy.LAST_WINS)
        repo.add_source(EnvFileSource(env_file))
        repo.add_source(TOMLSource(toml_file, section="tool.tripwire"))
        repo.load()

        # TOML (last) should override .env
        assert repo.get("port").value == 3000
        # HOST only in .env
        assert repo.get("HOST").value == "localhost"

    def test_load_multiple_sources_first_wins(self, tmp_path):
        """Test loading from multiple sources with first wins strategy."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 3000\n")

        repo = ConfigRepository(merge_strategy=MergeStrategy.FIRST_WINS)
        repo.add_source(EnvFileSource(env_file))
        repo.add_source(TOMLSource(toml_file, section="tool.tripwire"))
        repo.load()

        # .env (first) should win
        # Note: .env has PORT in uppercase, TOML has port in lowercase
        assert repo.get("PORT").value == "8000"
        assert repo.get("port").value == 3000  # Different key

    def test_load_strict_mode_no_conflicts(self, tmp_path):
        """Test strict mode with no conflicts."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text('[tool.tripwire]\nhost = "localhost"\n')

        repo = ConfigRepository(merge_strategy=MergeStrategy.STRICT)
        repo.add_source(EnvFileSource(env_file))
        repo.add_source(TOMLSource(toml_file, section="tool.tripwire"))

        # Should not raise
        repo.load()

        assert repo.get("PORT").value == "8000"
        assert repo.get("host").value == "localhost"

    def test_load_strict_mode_with_conflicts(self, tmp_path):
        """Test strict mode raises on conflicts."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nPORT = 3000\n")

        repo = ConfigRepository(merge_strategy=MergeStrategy.STRICT)
        repo.add_source(EnvFileSource(env_file))
        repo.add_source(TOMLSource(toml_file, section="tool.tripwire"))

        with pytest.raises(ValueError, match="Merge conflict in STRICT mode: PORT"):
            repo.load()

    def test_get_before_load_raises(self):
        """Test get raises if repository not loaded."""
        repo = ConfigRepository()

        with pytest.raises(RuntimeError, match="Repository not loaded"):
            repo.get("PORT")

    def test_get_nonexistent_key(self, tmp_path):
        """Test get returns None for nonexistent key."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        repo = ConfigRepository()
        repo.add_source(EnvFileSource(env_file))
        repo.load()

        assert repo.get("NONEXISTENT") is None

    def test_get_all(self, tmp_path):
        """Test get_all returns all config values."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\nDEBUG=true\n")

        repo = ConfigRepository()
        repo.add_source(EnvFileSource(env_file))
        repo.load()

        all_config = repo.get_all()

        assert len(all_config) == 3
        assert "PORT" in all_config
        assert "HOST" in all_config
        assert "DEBUG" in all_config

    def test_get_all_before_load_raises(self):
        """Test get_all raises if repository not loaded."""
        repo = ConfigRepository()

        with pytest.raises(RuntimeError, match="Repository not loaded"):
            repo.get_all()

    def test_diff_identical_repos(self, tmp_path):
        """Test diff with identical repositories."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\nHOST=localhost\n")

        repo1 = ConfigRepository.from_file(env_file).load()
        repo2 = ConfigRepository.from_file(env_file).load()

        diff = repo1.diff(repo2)

        assert not diff.has_changes
        assert len(diff.unchanged) == 2
        assert len(diff.added) == 0
        assert len(diff.removed) == 0
        assert len(diff.modified) == 0

    def test_diff_with_additions(self, tmp_path):
        """Test diff with added variables."""
        env_file1 = tmp_path / ".env"
        env_file1.write_text("PORT=8000\n")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("PORT=8000\nNEW_VAR=value\n")

        repo1 = ConfigRepository.from_file(env_file1).load()
        repo2 = ConfigRepository.from_file(env_file2).load()

        diff = repo1.diff(repo2)

        assert diff.has_changes
        assert "NEW_VAR" in diff.added
        assert len(diff.removed) == 0
        assert len(diff.modified) == 0

    def test_diff_with_removals(self, tmp_path):
        """Test diff with removed variables."""
        env_file1 = tmp_path / ".env"
        env_file1.write_text("PORT=8000\nOLD_VAR=value\n")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("PORT=8000\n")

        repo1 = ConfigRepository.from_file(env_file1).load()
        repo2 = ConfigRepository.from_file(env_file2).load()

        diff = repo1.diff(repo2)

        assert diff.has_changes
        assert "OLD_VAR" in diff.removed
        assert len(diff.added) == 0
        assert len(diff.modified) == 0

    def test_diff_with_modifications(self, tmp_path):
        """Test diff with modified variables."""
        env_file1 = tmp_path / ".env"
        env_file1.write_text("PORT=8000\nHOST=localhost\n")

        env_file2 = tmp_path / ".env.local"
        env_file2.write_text("PORT=3000\nHOST=localhost\n")

        repo1 = ConfigRepository.from_file(env_file1).load()
        repo2 = ConfigRepository.from_file(env_file2).load()

        diff = repo1.diff(repo2)

        assert diff.has_changes
        assert "PORT" in diff.modified
        old_val, new_val = diff.modified["PORT"]
        assert old_val.value == "8000"
        assert new_val.value == "3000"
        assert "HOST" in diff.unchanged

    def test_diff_before_load_raises(self, tmp_path):
        """Test diff raises if repositories not loaded."""
        repo1 = ConfigRepository()
        repo2 = ConfigRepository()

        with pytest.raises(RuntimeError, match="Both repositories must be loaded"):
            repo1.diff(repo2)

    def test_from_file_env(self, tmp_path):
        """Test from_file auto-detects .env format."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        repo = ConfigRepository.from_file(env_file)

        assert len(repo.sources) == 1
        assert isinstance(repo.sources[0], EnvFileSource)

    def test_from_file_env_variants(self, tmp_path):
        """Test from_file handles .env variants."""
        env_file = tmp_path / ".env.local"
        env_file.write_text("PORT=8000\n")

        repo = ConfigRepository.from_file(env_file)

        assert len(repo.sources) == 1
        assert isinstance(repo.sources[0], EnvFileSource)

    def test_from_file_toml(self, tmp_path):
        """Test from_file auto-detects TOML format."""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text("[tool.tripwire]\nport = 8000\n")

        repo = ConfigRepository.from_file(toml_file)

        assert len(repo.sources) == 1
        assert isinstance(repo.sources[0], TOMLSource)

    def test_from_file_unsupported_format(self, tmp_path):
        """Test from_file raises for unsupported formats."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("port: 8000\n")

        with pytest.raises(ValueError, match="Unsupported file format"):
            ConfigRepository.from_file(yaml_file)

    def test_from_file_chaining(self, tmp_path):
        """Test from_file can be chained with load."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        config = ConfigRepository.from_file(env_file).load().get("PORT")

        assert config.value == "8000"

    def test_load_skips_missing_files(self, tmp_path):
        """Test load skips missing files gracefully."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        missing_file = tmp_path / "missing.env"

        repo = ConfigRepository()
        repo.add_source(EnvFileSource(env_file))
        repo.add_source(EnvFileSource(missing_file))

        # Should not raise
        repo.load()

        assert repo.get("PORT").value == "8000"

    def test_cache_invalidation(self, tmp_path):
        """Test adding source invalidates cache."""
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n")

        repo = ConfigRepository()
        repo.add_source(EnvFileSource(env_file))
        repo.load()

        assert repo._config is not None

        # Adding source should invalidate cache
        repo.add_source(EnvFileSource(env_file))

        assert repo._config is None
